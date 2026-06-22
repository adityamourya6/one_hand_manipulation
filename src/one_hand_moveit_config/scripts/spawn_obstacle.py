#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from moveit_msgs.msg import CollisionObject
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose

class ObstacleSpawner(Node):
    def __init__(self):
        super().__init__('obstacle_spawner')
        self.collision_pub = self.create_publisher(CollisionObject, '/collision_object', 10)
        
    def spawn(self):
        self.get_logger().info('Publishing obstacle to MoveIt...')
        box = CollisionObject()
        box.header.frame_id = 'world'
        box.id = 'the_wall'
        box.operation = CollisionObject.ADD
        
        primitive = SolidPrimitive()
        primitive.type = SolidPrimitive.BOX
        primitive.dimensions = [0.05, 0.10, 0.30]  # depth, width, height
        
        # Place it dead center of the table, sticking up to block the swing
        pose = Pose()
        pose.position.x = 0.28
        pose.position.y = 0.00
        pose.position.z = 0.30
        pose.orientation.w = 1.0
        
        box.primitives.append(primitive)
        box.primitive_poses.append(pose)
        
        # Publish multiple times to ensure it is received
        for _ in range(5):
            self.collision_pub.publish(box)
            import time
            time.sleep(0.5)
        self.get_logger().info('Obstacle spawned!')

def main(args=None):
    rclpy.init(args=args)
    spawner = ObstacleSpawner()
    spawner.spawn()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
