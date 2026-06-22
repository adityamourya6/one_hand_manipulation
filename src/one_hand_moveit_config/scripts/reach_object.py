#!/usr/bin/env python3

import sys
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.parameter import Parameter

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import MotionPlanRequest, WorkspaceParameters, Constraints, PositionConstraint, OrientationConstraint, BoundingVolume
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import PoseStamped

class ReachObjectNode(Node):
    def __init__(self):
        super().__init__('reach_object_client', parameter_overrides=[Parameter('use_sim_time', Parameter.Type.BOOL, True)])
        self._action_client = ActionClient(self, MoveGroup, 'move_action')

    def send_goal(self):
        self.get_logger().info('Waiting for action server...')
        while not self._action_client.server_is_ready():
            self.get_logger().info('Waiting for /move_action server...')
            rclpy.spin_once(self, timeout_sec=1.0)

        goal_msg = MoveGroup.Goal()
        
        request = MotionPlanRequest()
        request.workspace_parameters.header.frame_id = 'world'
        request.workspace_parameters.min_corner.x = -1.0
        request.workspace_parameters.min_corner.y = -1.0
        request.workspace_parameters.min_corner.z = -1.0
        request.workspace_parameters.max_corner.x = 1.0
        request.workspace_parameters.max_corner.y = 1.0
        request.workspace_parameters.max_corner.z = 1.0
        
        request.group_name = 'fer_arm'
        request.num_planning_attempts = 10
        request.allowed_planning_time = 5.0
        request.max_velocity_scaling_factor = 0.5
        request.max_acceleration_scaling_factor = 0.5
        
        # Position Constraint
        p_const = PositionConstraint()
        p_const.header.frame_id = 'world'
        p_const.link_name = 'fer_link8'
        
        target_pose = PoseStamped()
        target_pose.header.frame_id = 'world'
        target_pose.pose.position.x = 0.28
        target_pose.pose.position.y = -0.20
        target_pose.pose.position.z = 0.50
        target_pose.pose.orientation.x = 1.0
        target_pose.pose.orientation.w = 0.0
        
        primitive = SolidPrimitive()
        primitive.type = SolidPrimitive.SPHERE
        primitive.dimensions = [0.01]  # 1 cm tolerance sphere
        
        p_const.constraint_region.primitives.append(primitive)
        p_const.constraint_region.primitive_poses.append(target_pose.pose)
        p_const.weight = 1.0
        
        # Orientation Constraint
        o_const = OrientationConstraint()
        o_const.header.frame_id = 'world'
        o_const.link_name = 'fer_link8'
        o_const.orientation = target_pose.pose.orientation
        o_const.absolute_x_axis_tolerance = 0.1
        o_const.absolute_y_axis_tolerance = 0.1
        o_const.absolute_z_axis_tolerance = 0.1
        o_const.weight = 1.0

        constraint = Constraints()
        constraint.position_constraints.append(p_const)
        constraint.orientation_constraints.append(o_const)
        
        request.goal_constraints.append(constraint)
        
        goal_msg.request = request
        
        self.get_logger().info('Sending goal request...')
        self._send_goal_future = self._action_client.send_goal_async(goal_msg)
        self._send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Goal rejected :(')
            return

        self.get_logger().info('Goal accepted :)')
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        result = future.result().result
        self.get_logger().info(f'Result code: {result.error_code.val}')
        if result.error_code.val == 1:
            self.get_logger().info('Execution SUCCESS!')
        else:
            self.get_logger().info('Execution FAILED.')
        rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    action_client = ReachObjectNode()
    action_client.send_goal()
    rclpy.spin(action_client)

if __name__ == '__main__':
    main()
