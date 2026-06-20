import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class JointStateListener(Node):
    """A ROS 2 node that subscribes to /joint_states and logs joint names and positions."""

    def __init__(self):
        super().__init__('joint_state_listener')
        self.subscription = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_state_callback,
            10,
        )
        self.get_logger().info('JointStateListener node started, subscribing to /joint_states')

    def joint_state_callback(self, msg: JointState):
        """Log the received joint names and positions."""
        self.get_logger().info('--- Joint States Received ---')
        for name, position in zip(msg.name, msg.position):
            self.get_logger().info(f'  Joint: {name}, Position: {position:.4f}')


def main(args=None):
    rclpy.init(args=args)
    node = JointStateListener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
