import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    pkg_share = FindPackageShare("one_hand_interface")
    
    # URDF
    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution([pkg_share, "urdf", "panda_mujoco.urdf.xacro"]),
        ]
    )
    robot_description = {"robot_description": ParameterValue(value=robot_description_content, value_type=str)}

    # SRDF
    robot_description_semantic_config = open(
        os.path.join(get_package_share_directory('one_hand_moveit_config'), 'config', 'fer.srdf'), 'r'
    ).read()
    robot_description_semantic = {'robot_description_semantic': robot_description_semantic_config}

    # Kinematics
    import yaml
    with open(os.path.join(get_package_share_directory('one_hand_moveit_config'), 'config', 'kinematics.yaml'), 'r') as file:
        kinematics_yaml = yaml.safe_load(file)

    with open(os.path.join(get_package_share_directory('one_hand_moveit_config'), 'config', 'ompl_planning.yaml'), 'r') as file:
        ompl_planning_yaml = yaml.safe_load(file)

    run_reach_object_node = Node(
        package='one_hand_moveit_config',
        executable='reach_object.py',
        output='screen',
        parameters=[
            robot_description,
            robot_description_semantic,
            kinematics_yaml,
            ompl_planning_yaml,
            {'use_sim_time': True},
        ],
    )

    return LaunchDescription([run_reach_object_node])
