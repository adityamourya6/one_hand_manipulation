import os
import launch
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue, ParameterFile
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory

def launch_setup(context, *args, **kwargs):
    pkg_share = FindPackageShare("one_hand_interface")
    pkg_share_dir = get_package_share_directory("one_hand_interface")

    # Select scene file based on collision_test argument
    collision_test = LaunchConfiguration("collision_test").perform(context)
    if collision_test.lower() in ("true", "1", "yes"):
        scene_file = os.path.join(pkg_share_dir, "config", "kitchen_scene_collision_test.xml")
    else:
        scene_file = os.path.join(pkg_share_dir, "config", "kitchen_scene.xml")

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
                {"mujoco_model": scene_file},
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
            DeclareLaunchArgument(
                "collision_test", default_value="false",
                description="Launch with a 10kg falling box above the robot arm to verify rigid body collisions."
            ),
            OpaqueFunction(function=launch_setup),
        ]
    )
