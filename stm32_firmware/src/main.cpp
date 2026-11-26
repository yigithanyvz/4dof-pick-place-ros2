#include <Arduino.h>
#include <ctype.h>
#include <micro_ros_arduino.h>
#include <stdio.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <geometry_msgs/msg/twist.h>

extern "C" {
  const char * __ctype_ptr__ = _ctype_;
  int _write(int file, char *ptr, int len) { return len; }
}

rcl_publisher_t publisher;
geometry_msgs__msg__Twist msg;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

#define LED_PIN PC13
#define RCCHECK(fn) { rcl_ret_t temp_rc = fn; if((temp_rc != RCL_RET_OK)){error_loop();}}
#define RCSOFTCHECK(fn) { rcl_ret_t temp_rc = fn; if((temp_rc != RCL_RET_OK)){}}

float apply_deadzone(int adc_value) {
  float norm_val = (adc_value - 512.0) / 512.0;
  if (norm_val > -0.20 && norm_val < 0.20) {
    return 0.0;
  }
  return norm_val;
}

void error_loop() {
  while (1) {
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    delay(100);
  }
}

void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  pinMode(PA2, INPUT_PULLUP);
  pinMode(PA5, INPUT_PULLUP);

  Serial.begin(115200);
  set_microros_transports();
  delay(2000);

  allocator = rcl_get_default_allocator();
  RCCHECK(rclc_support_init(&support, 0, NULL, &allocator));
  RCCHECK(rclc_node_init_default(&node, "joy_node", "", &support));

  RCCHECK(rclc_publisher_init_best_effort(
    &publisher,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist),
    "/cmd_vel"));

  digitalWrite(LED_PIN, HIGH);
}

void loop() {
  // SOL JOYSTICK: X ve Y (PA0 ve PA1) yer değiştirdi.
  // Eğer hareketlerden biri hala tersse, apply_deadzone başına eksi (-) koyabilirsin.
  msg.linear.x = apply_deadzone(analogRead(PA1)); 
  msg.linear.y = apply_deadzone(analogRead(PA0));
  msg.linear.z = (digitalRead(PA2) == LOW) ? 1.0 : 0.0;

  // SAĞ JOYSTICK: Yukarı itince aşağı indiği için PA4'ün yönü eksi (-) ile tersine çevrildi.
  msg.angular.x = apply_deadzone(analogRead(PA3));
  msg.angular.y = -apply_deadzone(analogRead(PA4)); // Yön tersine çevrildi
  msg.angular.z = (digitalRead(PA5) == LOW) ? 1.0 : 0.0;

  RCSOFTCHECK(rcl_publish(&publisher, &msg, NULL));
  delay(50); 
}