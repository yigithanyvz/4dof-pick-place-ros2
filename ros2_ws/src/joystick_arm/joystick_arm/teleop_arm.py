import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import Twist
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
from gazebo_msgs.srv import GetEntityState, SetEntityState

YESIL = '\033[92m'
SARI = '\033[93m'
MAVI = '\033[96m'
KIRMIZI = '\033[91m'
SIFIRLA = '\033[0m'

GRIP_OPEN = 0.002
GRIP_CLOSE = 0.0065  # Parmaklarin kupe surtup titremesini onleyen ideal kavrama araligi
KUPLER = ['kup_kirmizi', 'kup_yesil', 'kup_mavi']

class DualJoystickArmController(Node):
    def __init__(self):
        super().__init__('joystick_arm_controller')
        qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, history=HistoryPolicy.KEEP_LAST, depth=10)
        self.sub = self.create_subscription(Twist, '/cmd_vel', self.cmd_callback, qos)
        self.pub = self.create_publisher(JointTrajectory, '/set_joint_trajectory', 10)
        
        self.get_state_cli = self.create_client(GetEntityState, '/gazebo/get_entity_state')
        self.set_state_cli = self.create_client(SetEntityState, '/gazebo/set_entity_state')
        
        self.j1, self.j2, self.j3, self.j4, self.grip = 0.0, 0.0, 0.0, 0.0, GRIP_OPEN
        self.joy1_x, self.joy1_y = 0.0, 0.0
        self.joy2_x, self.joy2_y = 0.0, 0.0
        self.btn1, self.btn2 = False, False
        self.prev_btn1, self.prev_btn2 = False, False
        self.combo_lock = False
        
        self.sniper_mode = False
        self.grip_closed = False
        self.homing = False
        self.force_publish = True
        self.attached_cube = None
        
        self.timer = self.create_timer(0.02, self.update_arm)
        self.get_logger().info(f'{MAVI}=== 3B BİLEKLİ PICK & PLACE SİSTEMİ AKTİF ==={SIFIRLA}')

    def calc_tip_xyz(self, j1, j2, j3):
        # Parmaklarin tam orta kavrama noktasi (Taban: 0.20m, Omuz: 0.40m, Onkol+Kiskac ortasi: 0.41m)
        r = 0.40 * math.sin(j2) + 0.41 * math.sin(j2 + j3)
        z = 0.20 + 0.40 * math.cos(j2) + 0.41 * math.cos(j2 + j3)
        x = r * math.cos(j1)
        y = r * math.sin(j1)
        return x, y, z

    def calc_wrist_quaternion(self):
        # R_z(j1) * R_y(j2 + j3) * R_z(j4) tam 3B donus kuaterniyonu
        pitch = self.j2 + self.j3
        half_b = pitch / 2.0
        half_sum = (self.j1 + self.j4) / 2.0
        half_diff = (self.j1 - self.j4) / 2.0
        qw = math.cos(half_b) * math.cos(half_sum)
        qx = -math.sin(half_b) * math.sin(half_diff)
        qy = math.sin(half_b) * math.cos(half_diff)
        qz = math.cos(half_b) * math.sin(half_sum)
        return qx, qy, qz, qw

    def move_towards(self, current, target, step):
        diff = target - current
        if abs(diff) <= step:
            return target
        return current + step if diff > 0 else current - step

    def try_attach_nearest_cube(self):
        if not self.get_state_cli.service_is_ready():
            return
        gx, gy, gz = self.calc_tip_xyz(self.j1, self.j2, self.j3)
        for cube in KUPLER:
            req = GetEntityState.Request()
            req.name = cube
            future = self.get_state_cli.call_async(req)
            future.add_done_callback(lambda f, c=cube, x=gx, y=gy, z=gz: self.on_cube_checked(f, c, x, y, z))

    def on_cube_checked(self, future, cube_name, gx, gy, gz):
        if not self.grip_closed or self.attached_cube is not None:
            return
        try:
            res = future.result()
            if res and res.success:
                pos = res.state.pose.position
                dist = math.sqrt((pos.x - gx)**2 + (pos.y - gy)**2 + (pos.z - gz)**2)
                if dist < 0.16:
                    self.attached_cube = cube_name
                    self.get_logger().info(f'{MAVI}>>> [MIKNATIS KİLİTLENDİ]: {cube_name} <<<{SIFIRLA}')
        except Exception:
            pass

    def cmd_callback(self, msg: Twist):
        self.joy1_x = msg.linear.x if abs(msg.linear.x) > 0.08 else 0.0
        self.joy1_y = msg.linear.y if abs(msg.linear.y) > 0.08 else 0.0
        self.joy2_x = msg.angular.x if abs(msg.angular.x) > 0.08 else 0.0
        self.joy2_y = msg.angular.y if abs(msg.angular.y) > 0.08 else 0.0

        self.btn1 = msg.linear.z > 0.5
        self.btn2 = msg.angular.z > 0.5

        if self.homing and (self.joy1_x != 0.0 or self.joy1_y != 0.0 or self.joy2_x != 0.0 or self.joy2_y != 0.0):
            self.homing = False

        if self.btn1 and self.btn2:
            if not self.combo_lock:
                self.homing = True
                self.grip_closed = False
                self.attached_cube = None
                self.combo_lock = True
                self.get_logger().info(f'{MAVI}>>> [HOME RESET] Başlangıç konumuna süzülüyor... <<<{SIFIRLA}')
        else:
            if not self.btn1 and not self.btn2:
                self.combo_lock = False

            if self.btn1 and not self.prev_btn1 and not self.combo_lock:
                self.sniper_mode = not self.sniper_mode
                mod_adi = f'{SARI}HASSAS NİŞAN' if self.sniper_mode else f'{YESIL}SERİ TAŞIMA'
                self.get_logger().info(f'>>> MOD: {mod_adi}{SIFIRLA}')

            if self.btn2 and not self.prev_btn2 and not self.combo_lock:
                self.homing = False
                self.grip_closed = not self.grip_closed
                if self.grip_closed:
                    self.grip = GRIP_CLOSE
                    self.try_attach_nearest_cube()
                else:
                    self.grip = GRIP_OPEN
                    if self.attached_cube:
                        self.get_logger().info(f'{YESIL}>>> [BIRAKILDI]: {self.attached_cube} <<<{SIFIRLA}')
                    self.attached_cube = None
                self.force_publish = True

        self.prev_btn1 = self.btn1
        self.prev_btn2 = self.btn2

    def update_arm(self):
        if self.homing:
            home_step = 0.018
            self.j1 = self.move_towards(self.j1, 0.0, home_step)
            self.j2 = self.move_towards(self.j2, 0.0, home_step)
            self.j3 = self.move_towards(self.j3, 0.0, home_step)
            self.j4 = self.move_towards(self.j4, 0.0, home_step)
            self.grip = self.move_towards(self.grip, GRIP_OPEN, 0.001)
            if self.j1 == 0.0 and self.j2 == 0.0 and self.j3 == 0.0 and self.j4 == 0.0 and self.grip == GRIP_OPEN:
                self.homing = False
        else:
            speed = 0.008 if self.sniper_mode else 0.03
            wrist_speed = 0.018 if self.sniper_mode else 0.04
            moving = (self.joy1_x != 0.0 or self.joy1_y != 0.0 or self.joy2_x != 0.0 or self.joy2_y != 0.0)
            if moving or self.force_publish:
                cand_j1 = max(-3.13, min(3.13, self.j1 + self.joy1_x * speed))
                cand_j2 = max(-1.15, min(1.15, self.j2 + self.joy1_y * speed))
                cand_j3 = max(-1.45, min(1.45, self.j3 + self.joy2_y * speed))
                cand_j4 = max(-3.13, min(3.13, self.j4 + self.joy2_x * wrist_speed))

                _, _, cur_z = self.calc_tip_xyz(self.j1, self.j2, self.j3)
                _, _, new_z = self.calc_tip_xyz(cand_j1, cand_j2, cand_j3)

                self.j1 = cand_j1
                self.j4 = cand_j4
                if new_z >= 0.115 or new_z > cur_z:
                    self.j2 = cand_j2
                    self.j3 = cand_j3

        if self.attached_cube and self.set_state_cli.service_is_ready():
            gx, gy, gz = self.calc_tip_xyz(self.j1, self.j2, self.j3)
            qx, qy, qz, qw = self.calc_wrist_quaternion()
            req = SetEntityState.Request()
            req.state.name = self.attached_cube
            req.state.pose.position.x = float(gx)
            req.state.pose.position.y = float(gy)
            req.state.pose.position.z = float(max(0.115, gz))
            req.state.pose.orientation.x = float(qx)
            req.state.pose.orientation.y = float(qy)
            req.state.pose.orientation.z = float(qz)
            req.state.pose.orientation.w = float(qw)
            req.state.twist.linear.x = 0.0
            req.state.twist.linear.y = 0.0
            req.state.twist.linear.z = 0.0
            req.state.twist.angular.x = 0.0
            req.state.twist.angular.y = 0.0
            req.state.twist.angular.z = 0.0
            self.set_state_cli.call_async(req)

        traj = JointTrajectory()
        traj.header.frame_id = 'base_link'
        traj.joint_names = ['joint_1', 'joint_2', 'joint_3', 'joint_4', 'finger_left_joint', 'finger_right_joint']
        pt = JointTrajectoryPoint()
        pt.positions = [float(self.j1), float(self.j2), float(self.j3), float(self.j4), float(self.grip), float(self.grip)]
        pt.time_from_start = Duration(sec=0, nanosec=30000000)
        traj.points.append(pt)
        self.pub.publish(traj)
        self.force_publish = False

def main(args=None):
    rclpy.init(args=args)
    node = DualJoystickArmController()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
