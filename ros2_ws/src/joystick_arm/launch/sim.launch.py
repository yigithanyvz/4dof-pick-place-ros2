import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import xacro

def generate_launch_description():
    pkg_share = get_package_share_directory('joystick_arm')
    xacro_file = os.path.join(pkg_share, 'urdf', 'arm.urdf.xacro')
    robot_desc = xacro.process_file(xacro_file).toxml()
    world_path = os.path.join(pkg_share, 'worlds', 'pick_and_place.world')

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')]),
        launch_arguments={'world': world_path}.items()
    )
    robot_state_publisher = Node(package='robot_state_publisher', executable='robot_state_publisher', output='screen', parameters=[{'robot_description': robot_desc, 'use_sim_time': True}])
    spawn_entity = Node(package='gazebo_ros', executable='spawn_entity.py', arguments=['-topic', 'robot_description', '-entity', 'advanced_arm'], output='screen')
    teleop_node = Node(package='joystick_arm', executable='teleop_arm', output='screen', additional_env={'FASTDDS_BUILTIN_TRANSPORTS': 'UDPv4'})

    return LaunchDescription([gazebo, robot_state_publisher, spawn_entity, teleop_node])
