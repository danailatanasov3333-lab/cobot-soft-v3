import os
from modules.shared.MessageBroker import MessageBroker
from dataclasses import dataclass
from typing import Optional, List
import cv2
import numpy as np
from libs.plvision.PLVision import ImageProcessing
from libs.plvision.PLVision.Calibration import CameraCalibrator
import cv2.aruco as aruco


@dataclass
class CameraCalibrationServiceResult:
    """
    Result class for camera calibration operations.
    
    Contains all the data returned from a calibration operation including
    success status, calibration matrices, and diagnostic information.
    """
    success: bool
    message: str
    camera_matrix: Optional[np.ndarray] = None
    distortion_coefficients: Optional[np.ndarray] = None
    perspective_matrix: Optional[np.ndarray] = None
    rotation_vectors: Optional[List[np.ndarray]] = None
    translation_vectors: Optional[List[np.ndarray]] = None
    valid_images_count: int = 0
    calibration_error: Optional[float] = None
    storage_path: Optional[str] = None
    
    @property
    def calibration_data(self) -> Optional[List[np.ndarray]]:
        """
        Legacy format: [distortion_coefficients, camera_matrix]
        For backward compatibility with existing code.
        """
        if self.success and self.distortion_coefficients is not None and self.camera_matrix is not None:
            return [self.distortion_coefficients, self.camera_matrix]
        return None
    
    @property
    def is_calibrated(self) -> bool:
        """Check if calibration was successful and has valid data."""
        return (self.success and 
                self.camera_matrix is not None and 
                self.distortion_coefficients is not None)
    
    def to_legacy_tuple(self) -> tuple:
        """
        Convert to legacy tuple format for backward compatibility.
        Returns: (success, calibration_data, perspective_matrix, message)
        """
        return (self.success, self.calibration_data, self.perspective_matrix, self.message)


class CameraCalibrationService:
    # Default storage path: folder next to this module under 'storage/calibration_result'
    DEFAULT_STORAGE_PATH = os.path.join(os.path.dirname(__file__), 'storage', 'calibration_result')

    def __init__(self, chessboardWidth, chessboardHeight, squareSizeMM, skipFrames,message_publisher,storagePath,onDetectionFailed=None, ):
        # Determine storage path priority:
        # 1. Explicitly passed storagePath
        # 3. Default global path
        if storagePath is None:
            raise ValueError("Storage path cannot be None")
        self.STORAGE_PATH = storagePath
        print(f"📁 CameraCalibrationService: Using storage path: {self.STORAGE_PATH}")

        # Ensure storage directory exists
        if not os.path.exists(self.STORAGE_PATH):
            os.makedirs(self.STORAGE_PATH, exist_ok=True)
            print(f"📁 Created calibration storage directory: {self.STORAGE_PATH}")

        self.calibrationImages = []
        self.chessboardWidth = chessboardWidth
        self.chessboardHeight = chessboardHeight
        self.squareSizeMM = squareSizeMM
        self.skipFrames = skipFrames
        self.message_publisher = message_publisher
        self.onDetectionFailed = onDetectionFailed
        self.cameraCalibrator = CameraCalibrator(self.chessboardWidth, self.chessboardHeight, self.squareSizeMM)

        self.messageBroker = MessageBroker()
    
    @property
    def PERSPECTIVE_MATRIX_PATH(self):
        """Dynamic path to perspective transform matrix file"""
        return os.path.join(self.STORAGE_PATH, 'perspectiveTransform.npy')
    
    @property 
    def CAMERA_TO_ROBOT_MATRIX_PATH(self):
        """Dynamic path to camera-to-robot matrix file"""
        return os.path.join(self.STORAGE_PATH, 'cameraToRobotMatrix.npy')

    def detectArucoMarkers(self, flip=False, image=None):
        """
        Detects ArUco markers in the provided image.
        Returns corners, ids, and the (possibly flipped) image.
        """
        if image is None:
            print("No image provided for ArUco detection.")
            return None, None, None

        if flip:
            image = cv2.flip(image, 1)

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_250)
        parameters = aruco.DetectorParameters()
        detector = aruco.ArucoDetector(dictionary, parameters)

        try:
            corners, ids, _ = detector.detectMarkers(gray)
            if ids is not None:
                print(f"✅ Detected ArUco IDs: {ids.flatten()}")
            else:
                print("❌ No ArUco markers detected")
            return corners, ids, image
        except Exception as e:
            print(f"❌ ArUco Detection failed: {e}")
            return None, None, image

    def detectPerspectiveCorrectionMarkers(self, image):
        """
        Detect ArUco markers (IDs 30, 31, 32, 33) for perspective correction.
        Returns corners in order: top-left (30), top-right (31), bottom-right (32), bottom-left (33)
        """
        required_marker_ids = [30, 31, 32, 33]  # top-left, top-right, bottom-right, bottom-left
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_250)
        parameters = aruco.DetectorParameters()
        detector = aruco.ArucoDetector(dictionary, parameters)
        
        try:
            corners, ids, _ = detector.detectMarkers(gray)
            if ids is None:
                return False, None, "No ArUco markers detected for perspective correction"
            
            # Create a mapping of marker ID to corners
            marker_corners = {}
            for i, marker_id in enumerate(ids.flatten()):
                if marker_id in required_marker_ids:
                    # Get the top-left corner of each marker
                    marker_corners[marker_id] = corners[i][0][0]  # top-left corner
            
            # Check if all required markers are found
            missing_markers = [mid for mid in required_marker_ids if mid not in marker_corners]
            if missing_markers:
                return False, None, f"Missing perspective correction markers: {missing_markers}"
            
            # Order corners: top-left (30), top-right (31), bottom-right (32), bottom-left (33)
            ordered_corners = [
                marker_corners[30],  # top-left
                marker_corners[31],  # top-right
                marker_corners[32],  # bottom-right
                marker_corners[33]   # bottom-left
            ]
            
            return True, ordered_corners, "Perspective correction markers detected successfully"
            
        except Exception as e:
            return False, None, f"Error detecting perspective correction markers: {str(e)}"
    
    def computePerspectiveCorrection(self, image, src_corners, output_size=(1280, 720)):
        """
        Compute perspective transformation matrix and apply correction.
        """
        # Define destination rectangle (rectified image)
        dst_corners = np.array([
            [0, 0],                           # top-left
            [output_size[0] - 1, 0],         # top-right
            [output_size[0] - 1, output_size[1] - 1],  # bottom-right
            [0, output_size[1] - 1]          # bottom-left
        ], dtype=np.float32)
        
        src_corners = np.array(src_corners, dtype=np.float32)
        
        # Compute perspective transformation matrix
        perspective_matrix = cv2.getPerspectiveTransform(src_corners, dst_corners)
        
        # Apply perspective correction
        corrected_image = cv2.warpPerspective(image, perspective_matrix, output_size)
        
        return corrected_image, perspective_matrix

    def cleanupOldCalibrationFiles(self):
        """
        Delete old calibration files to ensure fresh calibration.
        """
        files_to_delete = [
            os.path.join(self.STORAGE_PATH, 'perspectiveTransform.npy'),
            os.path.join(self.STORAGE_PATH, 'calibration_data.npz'),
            os.path.join(self.STORAGE_PATH, 'camera_calibration.npz')
        ]
        
        for file_path in files_to_delete:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"🗑️ Deleted old calibration file: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"⚠️ Could not delete {file_path}: {e}")

    def run(self, image, debug=True) -> CameraCalibrationServiceResult:
        """
        Main calibration workflow with perspective correction support.
        Returns CameraCalibrationServiceResult containing all calibration data.
        """
        message = ""
        
        # Clean up old calibration files at the start
        self.cleanupOldCalibrationFiles()

        if not self.calibrationImages or len(self.calibrationImages) <= 0:
            message = "No calibration images provided"
            self.publish(message)
            print(message)
            return CameraCalibrationServiceResult(
                success=False,
                message=message
            )
        
        # Track if perspective correction was applied
        perspective_matrix_for_vision = None
        
        # If we have only one image, try perspective correction with ArUco markers
        if len(self.calibrationImages) == 1:
            print("Single image detected - attempting perspective correction with ArUco markers")
            single_image = self.calibrationImages[0]
            
            # Detect perspective correction markers
            success, corners, detect_message = self.detectPerspectiveCorrectionMarkers(single_image)
            if success:
                print(f"✅ {detect_message}")
                self.publish(detect_message)
                
                # Apply perspective correction
                corrected_image, perspective_matrix_for_vision = self.computePerspectiveCorrection(single_image, corners)
                
                # Save the corrected image for debugging
                corrected_path = os.path.join(self.STORAGE_PATH, 'perspective_corrected.png')
                cv2.imwrite(corrected_path, corrected_image)
                print(f"📸 Perspective corrected image saved to: {corrected_path}")
                
                # Test chessboard detection on corrected image before proceeding
                gray_corrected = cv2.cvtColor(corrected_image, cv2.COLOR_BGR2GRAY)
                chessboard_size = (self.chessboardWidth, self.chessboardHeight)
                ret_test, corners_test = cv2.findChessboardCorners(gray_corrected, chessboard_size, None)
                
                if ret_test:
                    print(f"✅ Chessboard detected in perspective-corrected image: {len(corners_test)} corners")
                else:
                    print(f"⚠️ Chessboard NOT detected in perspective-corrected image")
                    print(f"   Expected chessboard size: {chessboard_size[0]}x{chessboard_size[1]} = {chessboard_size[0] * chessboard_size[1]} corners")
                    print(f"   Trying different detection flags...")
                    
                    # Try with different flags
                    flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE + cv2.CALIB_CB_FILTER_QUADS
                    ret_test, corners_test = cv2.findChessboardCorners(gray_corrected, chessboard_size, flags)
                    
                    if ret_test:
                        print(f"✅ Chessboard detected with alternative flags: {len(corners_test)} corners")
                    else:
                        print(f"❌ Chessboard still not detected - check image quality and chessboard size")
                        print(f"   Image size after correction: {corrected_image.shape[1]}x{corrected_image.shape[0]}")
                
                # Replace the original image with the corrected one
                self.calibrationImages = [corrected_image]
                
                message = "Perspective correction applied successfully"
                self.publish(message)
            else:
                print(f"❌ {detect_message}")
                self.publish(detect_message)
                print("Proceeding with calibration without perspective correction")

        # Prepare object points
        chessboard_size = (self.chessboardWidth, self.chessboardHeight)
        square_size = self.squareSizeMM
        objp = np.zeros((np.prod(chessboard_size), 3), np.float32)
        objp[:, :2] = np.mgrid[0:chessboard_size[0], 0:chessboard_size[1]].T.reshape(-1, 2)
        objp *= square_size

        objpoints = []  # 3d points in real world space
        imgpoints = []  # 2d points in image plane

        message = f"Processing {len(self.calibrationImages)} images for chessboard detection..."
        self.publish(message)
        print(message)

        valid_images = 0
        for idx, img in enumerate(self.calibrationImages):
            if img is None:
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Find the chessboard corners
            ret, corners = cv2.findChessboardCorners(gray, chessboard_size, None)

            if ret:
                objpoints.append(objp)

                # Refine corner positions
                corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1),
                                            criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
                imgpoints.append(corners2)

                # Draw and save the corners for visualization
                cv2.drawChessboardCorners(img, chessboard_size, corners2, ret)
                output_path = os.path.join(self.STORAGE_PATH, f'calib_result_{idx:03d}.png')
                cv2.imwrite(output_path, img)

                valid_images += 1
                print(f"✅ Chessboard detected in image {idx}")
                message = f"✅ Chessboard detected in image {idx} - saved to {output_path}"
                self.publish(message)
            else:
                print(f"❌ No chessboard found in image {idx}")
                message = f"❌ No chessboard found in image {idx}"
                self.publish(message)

        if valid_images < 1:  # Need at least 1 good images for calibration
            message = f"Insufficient valid images for calibration. Found {valid_images}, need at least 1."
            print(f"❌ {message}")
            self.publish(message)
            return CameraCalibrationServiceResult(
                success=False,
                message=message
            )

        # Perform camera calibration
        print(f"🔧 Performing calibration with {valid_images} valid images...")
        message = f"🔧 Performing calibration with {valid_images} valid images..."
        self.publish(message)

        try:
            ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
                objpoints, imgpoints, gray.shape[::-1], None, None
            )

            if ret:
                # Save calibration results in both formats for compatibility
                calibration_file = os.path.join(self.STORAGE_PATH, 'calibration_data.npz')
                np.savez(calibration_file,
                         camera_matrix=camera_matrix,
                         dist_coeffs=dist_coeffs,
                         rvecs=rvecs,
                         tvecs=tvecs)
                
                # Also save in the old format for VisionSystem compatibility
                old_calibration_file = os.path.join(self.STORAGE_PATH, 'camera_calibration.npz')
                np.savez(old_calibration_file,
                         mtx=camera_matrix,
                         dist=dist_coeffs)
                
                # Save perspective matrix if it was computed (for single image with ArUco markers)
                if perspective_matrix_for_vision is not None:
                    perspective_file = os.path.join(self.STORAGE_PATH, 'perspectiveTransform.npy')
                    np.save(perspective_file, perspective_matrix_for_vision)
                    print(f"🔄 Perspective transformation matrix saved to: {perspective_file}")
                    message = "Perspective transformation matrix saved"
                    self.publish(message)

                # Store in instance variables
                self.camera_matrix = camera_matrix
                self.dist_coeffs = dist_coeffs
                self.calibrated = True

                print("✅ Camera calibration completed successfully!")
                message = "✅ Camera calibration completed successfully!"
                self.publish(message)

                print(f"📊 Calibration parameters saved to: {calibration_file}")
                print(f"📊 Legacy format saved to: {old_calibration_file}")
                message = f"📊 Calibration parameters saved successfully"
                self.publish(message)

                message = f"Calibration successful with {valid_images} images"
                self.publish(message)
                return CameraCalibrationServiceResult(
                    success=True,
                    message=message,
                    camera_matrix=camera_matrix,
                    distortion_coefficients=dist_coeffs,
                    perspective_matrix=perspective_matrix_for_vision,
                )
            else:
                message = "Camera calibration failed during cv2.calibrateCamera"
                print(f"❌ {message}")
                self.publish(message)
                return CameraCalibrationServiceResult(
                    success=False,
                    message=message
                )

        except Exception as e:
            import traceback
            traceback.print_exc()
            message = f"Exception during calibration: {str(e)}"
            self.publish(message)
            return CameraCalibrationServiceResult(
                success=False,
                message=message
            )

    def publish(self,message):
        if self.message_publisher is None:
            return
        self.message_publisher.publish_calibration_feedback(message)
