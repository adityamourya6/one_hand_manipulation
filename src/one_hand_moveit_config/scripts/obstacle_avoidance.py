#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import CollisionObject, PlanningOptions
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose, PoseStamped
import time

class ObstacleAvoidanceClient(Node):
    def __init__(self):
        super().__init__('obstacle_avoidance_client')
        
        # Publisher to add obstacles to MoveIt's planning scene
        self.collision_pub = self.create_publisher(CollisionObject, '/collision_object', 10)
        
        # Action client for MoveIt
        self._action_client = ActionClient(self, MoveGroup, 'move_action')
        
    def add_obstacle(self):
        self.get_logger().info('Adding a floating obstacle to the scene...')
        
        box = CollisionObject()
        box.header.frame_id = 'world'
        box.id = 'floating_barrier'
        box.operation = CollisionObject.ADD
        
        # Create a wall-like box
        primitive = SolidPrimitive()
        primitive.type = SolidPrimitive.BOX
        primitive.dimensions = [0.1, 0.1, 0.1]  # depth (x), width (y), height (z)
        
        # Place it exactly in the middle of the swing path (y=0)
        pose = Pose()
        pose.position.x = 0.28
        pose.position.y = 0.0
        pose.position.z = 0.50
        pose.orientation.w = 1.0
        
        box.primitives.append(primitive)
        box.primitive_poses.append(pose)
        
        # Publish it
        self.collision_pub.publish(box)
        time.sleep(1.0) # Give MoveIt a moment to register the obstacle
        
    def send_goal(self):
        self.get_logger().info('Waiting for action server...')
        self._action_client.wait_for_server()
        
        goal_msg = MoveGroup.Goal()
        
        # Set planning group
        goal_msg.request.group_name = 'fer_arm'
        goal_msg.request.num_planning_attempts = 10
        goal_msg.request.allowed_planning_time = 5.0
        goal_msg.request.max_velocity_scaling_factor = 0.5
        goal_msg.request.max_acceleration_scaling_factor = 0.5
        
        # Target coordinate: Swing back to the other side (y=0.20)
        target_pose = PoseStamped()
        target_pose.header.frame_id = 'world'
        target_pose.pose.position.x = 0.28
        target_pose.pose.position.y = 0.20
        target_pose.pose.position.z = 0.50
        
        # Keep gripper pointing straight out
        target_pose.pose.orientation.x = 1.0
        target_pose.pose.orientation.w = 0.0
        
        # Create constraint
        from moveit_msgs.msg import Constraints, PositionConstraint, OrientationConstraint, BoundingVolume
        
        pos_constraint = PositionConstraint()
        pos_constraint.link_name = 'fer_link8'
        pos_constraint.header.frame_id = 'world'
        
        # Small tolerance sphere
        volume = BoundingVolume()
        sphere = SolidPrimitive()
        sphere.type = SolidPrimitive.SPHERE
        sphere.dimensions = [0.01]
        volume.primitives.append(sphere)
        volume.primitive_poses.append(target_pose.pose)
        pos_constraint.constraint_region = volume
        pos_constraint.weight = 1.0
        
        ori_constraint = OrientationConstraint()
        ori_constraint.link_name = 'fer_link8'
        ori_constraint.header.frame_id = 'world'
        ori_constraint.orientation = target_pose.pose.orientation
        ori_constraint.absolute_x_axis_tolerance = 3.14
        ori_constraint.absolute_y_axis_tolerance = 3.14
        ori_constraint.absolute_z_axis_tolerance = 3.14
        ori_constraint.weight = 1.0
        
        goal_msg.request.goal_constraints = [Constraints(
            position_constraints=[pos_constraint],
            orientation_constraints=[ori_constraint]
        )]
        
        # We want to actually move!
        goal_msg.planning_options.plan_only = False
        goal_msg.planning_options.look_around = False
        goal_msg.planning_options.replan = True
        
        self.get_logger().info('Sending goal request to reach behind the obstacle...')
        self._send_goal_future = self._action_client.send_goal_async(goal_msg)
        self._send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Goal rejected by MoveIt :(')
            return
        
        self.get_logger().info('Goal accepted! Planning and moving...')
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        result = future.result().result
        self.get_logger().info(f'Result code: {result.error_code.val}')
        if result.error_code.val == 1:
            self.get_logger().info('Execution SUCCESS! Obstacle successfully avoided!')
        else:
            self.get_logger().info('Execution FAILED!')
        rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    client = ObstacleAvoidanceClient()
    
    # Add the obstacle to the scene first
    client.add_obstacle()
    
    # Send the motion request
    client.send_goal()
    
    rclpy.spin(client)

if __name__ == '__main__':
    main()
