import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'joystick_arm'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*')),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*')),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='yigithan',
    maintainer_email='yigithan2007yavuz@gmail.com',
    description='STM32 Joystick ile Gazebo Robot Kol Kontrolu',
    license='MIT',
    entry_points={'console_scripts': ['teleop_arm = joystick_arm.teleop_arm:main']},
)
