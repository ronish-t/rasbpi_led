#!/usr/bin/env python3
import board
import neopixel
import json
import asyncio
import websockets
import signal
import sys
from time import sleep

# Configuration - REPLACE WITH YOUR SERVER URL
WEBSOCKET_URL = "wss://pumped-drum-amazingly.ngrok-free.app"
LED_COUNT = 30          # Number of LEDs in your strip
LED_PIN = board.D18      # GPIO pin connected to data line
LED_BRIGHTNESS = 0.5     # Initial brightness (0.0-1.0)
RECONNECT_DELAY = 5      # Seconds between connection attempts

class LEDController:
    def __init__(self):
        self.pixels = neopixel.NeoPixel(
            LED_PIN,
            LED_COUNT,
            brightness=LED_BRIGHTNESS,
            auto_write=False
        )
        self.current_color = (0, 0, 0)
    
    def set_color(self, hex_color):
        """Set all LEDs to specified hex color"""
        rgb = self.hex_to_rgb(hex_color)
        if rgb != self.current_color:
            self.current_color = rgb
            self.pixels.fill(rgb)
            self.pixels.show()
            print(f"LEDs set to {hex_color}")

    @staticmethod
    def hex_to_rgb(hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def cleanup(self):
        """Turn off all LEDs and cleanup resources"""
        self.pixels.fill((0, 0, 0))
        self.pixels.show()
        print("LEDs cleared")

class WebSocketClient:
    def __init__(self, led_controller):
        self.led = led_controller
        self.running = True
        self.websocket = None

    async def connect(self):
        """Manage WebSocket connection with retries"""
        while self.running:
            try:
                async with websockets.connect(
                    WEBSOCKET_URL,
                    ping_interval=None
                ) as self.websocket:
                    await self.register()
                    await self.listen()
            except Exception as e:
                print(f"Connection error: {str(e)}")
                print(f"Reconnecting in {RECONNECT_DELAY} seconds...")
                await asyncio.sleep(RECONNECT_DELAY)

    async def register(self):
        """Register as a Python client"""
        await self.websocket.send(json.dumps({
            "type": "register",
            "clientType": "python"
        }))
        print("Registered with WebSocket server")

    async def listen(self):
        """Listen for incoming messages"""
        async for message in self.websocket:
            try:
                data = json.loads(message)
                self.handle_message(data)
            except json.JSONDecodeError:
                print("Received invalid JSON")
            except Exception as e:
                print(f"Message handling error: {str(e)}")

    def handle_message(self, data):
        """Process different message types"""
        if data.get("type") in ["speaker", "subtitle"]:
            color = data.get("color", "#000000")
            self.led.set_color(color)
            print(f"Received color update: {color}")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\nShutting down...")
    client.running = False
    led_controller.cleanup()
    sys.exit(0)

if __name__ == "__main__":
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Initialize components
    led_controller = LEDController()
    client = WebSocketClient(led_controller)

    try:
        # Start main event loop
        asyncio.get_event_loop().run_until_complete(client.connect())
    finally:
        led_controller.cleanup()