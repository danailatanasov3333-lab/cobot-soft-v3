from core.services.robot_service.impl.robot_monitor.subscription_manager import BaseSubscriptionManager


class GlueRobotServiceSubscriptionManager(BaseSubscriptionManager):
    def __init__(self, robot_service, broker):
        self.robot_service = robot_service
        self.broker = broker
        super().__init__(self.robot_service, self.broker)

        self.glue_process_state_topic = "glue-process/state"


    def subscribe_all(self):
        self.subscribe_glue_process_state_topic()


    def subscribe_glue_process_state_topic(self):
        self._add_subscription(self.glue_process_state_topic,
                               self.robot_service.state_manager.on_glue_process_state_update)

    def unsubscribe_glue_process_state_topic(self):
        self._remove_subscription(self.glue_process_state_topic)
