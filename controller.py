#!/usr/bin/env python3
import json
import asyncio
import websockets
import signal
import sys
import re
from time import sleep

# Raspberry Pi GPIO configuration
try:
    import RPi.GPIO as GPIO
    PI_AVAILABLE = True
except ImportError:
    print("Warning: RPi.GPIO not available. Running in simulation mode.")
    PI_AVAILABLE = False

# Configuration - UPDATE THIS TO YOUR SERVER'S URL
WEBSOCKET_URL = "wss://pumped-drum-amazingly.ngrok-free.app"  
RECONNECT_DELAY = 5 

# GPIO pin configuration for RGB LED
RED_PIN = 17    # GPIO 17
GREEN_PIN = 27  # GPIO 27
BLUE_PIN = 22   # GPIO 22

class LEDController:
    def __init__(self):
        self.current_color = None
        self.running = True
        self._setup_gpio()

    def _setup_gpio(self):
        """Initialize GPIO pins and PWM channels"""
        if not PI_AVAILABLE:
            return

        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(RED_PIN, GPIO.OUT)
            GPIO.setup(GREEN_PIN, GPIO.OUT)
            GPIO.setup(BLUE_PIN, GPIO.OUT)

            self.red_pwm = GPIO.PWM(RED_PIN, 100)
            self.green_pwm = GPIO.PWM(GREEN_PIN, 100)
            self.blue_pwm = GPIO.PWM(BLUE_PIN, 100)

            self.red_pwm.start(0)
            self.green_pwm.start(0)
            self.blue_pwm.start(0)
            print("GPIO initialized successfully")
        except Exception as e:
            print(f"GPIO initialization failed: {e}")
            self.running = False

    def cleanup(self):
        """Clean up GPIO resources"""
        if PI_AVAILABLE:
            print("Cleaning up GPIO...")
            self.red_pwm.stop()
            self.green_pwm.stop()
            self.blue_pwm.stop()
            GPIO.cleanup()

    def set_color(self, hex_color):
        """Set LED color from hex code (#RRGGBB)"""
        if hex_color == self.current_color:
            return

        self.current_color = hex_color
        r, g, b = self._hex_to_rgb(hex_color)
        
        # Convert to PWM duty cycles (0-100)
        r_duty = (r / 255) * 100
        g_duty = (g / 255) * 100
        b_duty = (b / 255) * 100

        print(f"Setting color: {hex_color} (R: {r_duty:.1f}%, G: {g_duty:.1f}%, B: {b_duty:.1f}%)")

        if PI_AVAILABLE:
            self.red_pwm.ChangeDutyCycle(r_duty)
            self.green_pwm.ChangeDutyCycle(g_duty)
            self.blue_pwm.ChangeDutyCycle(b_duty)

    @staticmethod
    def _hex_to_rgb(hex_color):
        """Convert hex color string to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
            
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

class WebSocketClient:
    def __init__(self, led_controller):
        self.led_controller = led_controller
        self.websocket = None
        self.running = True

    async def connect(self):
        """Manage WebSocket connection with retries"""
        while self.running:
            try:
                print(f"Connecting to {WEBSOCKET_URL}...")
                async with websockets.connect(
                    WEBSOCKET_URL,
                    ssl=True if WEBSOCKET_URL.startswith('wss') else None
                ) as ws:
                    self.websocket = ws
                    await self._register_client()
                    await self._listen_messages()
                    
            except Exception as e:
                print(f"Connection error: {e}")
                await asyncio.sleep(RECONNECT_DELAY)

    async def _register_client(self):
        """Register as a Python client with the server"""
        await self.websocket.send(json.dumps({
            "type": "register",
            "clientType": "python"
        }))
        print("Successfully registered as Python client")

    async def _listen_messages(self):
        """Process incoming WebSocket messages"""
        async for message in self.websocket:
            try:
                data = json.loads(message)
                self._handle_message(data)
            except json.JSONDecodeError:
                print(f"Invalid JSON received: {message}")
            except Exception as e:
                print(f"Error processing message: {e}")

    def _handle_message(self, data):
        """Handle different message types from server"""
        if data.get("type") in ["speaker", "subtitle"]:
            self._handle_subtitle(data)
        else:
            print(f"Received unknown message type: {data.get('type')}")

    def _handle_subtitle(self, data):
        """Process subtitle/speaker messages"""
        speaker = data.get("name", "unknown")
        color = data.get("color", "#FFFFFF")
        text = data.get("text", "")
        
        print(f"\n[{speaker}]: {text}")
        self.led_controller.set_color(color)

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\nShutting down...")
    client.running = False
    led_controller.running = False
    led_controller.cleanup()
    sys.exit(0)

if __name__ == "__main__":
    # Setup signal handling
    signal.signal(signal.SIGINT, signal_handler)

    # Initialize components
    led_controller = LEDController()
    client = WebSocketClient(led_controller)

    # Run main loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.connect())
    finally:
        led_controller.cleanup()
        loop.close()