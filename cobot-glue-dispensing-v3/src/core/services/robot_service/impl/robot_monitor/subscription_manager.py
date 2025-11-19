from core.services.robot_service.impl.base_robot_service import BaseRobotService


class BaseSubscriptionManager:
    def __init__(self,robot_service:BaseRobotService,broker):
        self.robot_service = robot_service
        self.broker = broker
        self.subscriptions = {}

    def subscribe_all(self):
        self.subscribe_robot_state_topic()

    def subscribe_robot_state_topic(self):
        self._add_subscription(self.robot_service.robot_state_manager.robotStateTopic, self.robot_service.state_manager.onRobotStateUpdate)

    def unsubscribe_robot_state_topic(self):
        self._remove_subscription(self.robot_service.robot_state_manager.robotStateTopic)

    def _add_subscription(self, topic, callback):
        self.broker.subscribe(topic, callback)
        self.subscriptions[topic] = callback

    def _remove_subscription(self, topic):
        if topic in self.subscriptions:
            self.broker.unsubscribe(topic, self.subscriptions[topic])
            del self.subscriptions[topic]