import os
import launch
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue, ParameterFile
from launch_ros.substitutions import FindPackageShare

def launch_setup(context, *args, **kwargs):
    pkg_share = FindPackageShare("one_hand_interface")

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution([pkg_share, "urdf", "panda_mujoco.urdf.xacro"]),
        ]
    )
    robot_description_str = robot_description_content.perform(context)
    robot_description = {"robot_description": ParameterValue(value=robot_description_str, value_type=str)}

    parameters_file = PathJoinSubstitution([pkg_share, "config", "controllers.yaml"])

    nodes = []

    # Robot state publisher
    nodes.append(
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            output="both",
            parameters=[robot_description, {"use_sim_time": True}],
        )
    )

    # ros2_control node with MuJoCo
    nodes.append(
        Node(
            package="mujoco_ros2_control",
            executable="ros2_control_node",
            emulate_tty=True,
            output="both",
            parameters=[
                robot_description,
                {"use_sim_time": True},
                ParameterFile(parameters_file),
            ],
            remappings=[
                ("~/robot_description", "/robot_description"),
            ]
        )
    )

    # Controller spawners
    controllers_to_spawn = ["joint_state_broadcaster", "fer_arm_controller", "fer_gripper_controller"]
    for controller in controllers_to_spawn:
        nodes.append(
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=[controller],
                output="both",
            )
        )

    rviz_config_file = PathJoinSubstitution([pkg_share, "rviz", "view_robot.rviz"])

    # RViz node
    nodes.append(
        Node(
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            output="log",
            arguments=["-d", rviz_config_file],
            condition=launch.conditions.IfCondition(LaunchConfiguration("rviz")),
        )
    )

    return nodes

def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "rviz", default_value="true", description="Start RViz2 automatically with this launch file."
            ),
            OpaqueFunction(function=launch_setup),
        ]
    )
