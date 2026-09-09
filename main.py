import threading
import asyncio
import json
import zlib
import websockets
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock

class SniperApp(App):
    def build(self):
        self.title = "Sniper Engine"
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        layout.add_widget(Label(text='Target Pair (e.g. btc_usdt, sol_usdt):', size_hint_y=None, height=30))
        
        self.pair_input = TextInput(text='btc_usdt', multiline=False, size_hint_y=None, height=50)
        layout.add_widget(self.pair_input)
        
        self.start_btn = Button(text='Start Sniper Engine', size_hint_y=None, height=60, background_color=(0.1, 0.6, 0.3, 1))
        self.start_btn.bind(on_press=self.start_engine)
        layout.add_widget(self.start_btn)
        
        self.status_label = Label(text='Status: ⚪ WAITING TO START', halign='center', valign='middle')
        self.status_label.bind(size=self.status_label.setter('text_size'))
        layout.add_widget(self.status_label)
        
        self.running = False
        return layout

    def start_engine(self, instance):
        if not self.running:
            self.running = True
            self.start_btn.text = 'Running...'
            self.start_btn.background_color = (0.8, 0.2, 0.2, 1)
            target_pair = self.pair_input.text.strip().lower()
            threading.Thread(target=self.run_async_loop, args=(target_pair,), daemon=True).start()

    def run_async_loop(self, pair):
        asyncio.run(self.websocket_worker(pair))

    async def websocket_worker(self, user_pair):
        uri = "wss://api.lbank.info/ws/V2/"
        price_history = []
        
        while self.running:
            try:
                async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as websocket:
                    sub_msg = {
                        "action": "subscribe",
                        "subscribe": "depth",
                        "pair": user_pair,
                        "depth": "50"
                    }
                    await websocket.send(json.dumps(sub_msg))
                    
                    while self.running:
                        response = await websocket.recv()
                        if isinstance(response, bytes):
                            decompressed = zlib.decompress(response, 16 + zlib.MAX_WBITS)
                            data = json.loads(decompressed.decode('utf-8'))
                        else:
                            data = json.loads(response)
                        
                        if "ping" in data:
                            await websocket.send(json.dumps({"pong": data["ping"]}))
                            continue
                        
                        depth_data = data.get("depth", {})
                        bids = depth_data.get("bids", [])
                        if not bids:
                            continue
                        
                        mid_price = float(bids[0][0])
                        price_history.append(mid_price)
                        if len(price_history) > 50:
                            price_history.pop(0)
                        
                        info_text = f"Pair: {user_pair.upper()}\nLive Price: {mid_price:.2f} USDT\nSamples: {len(price_history)}"
                        Clock.schedule_once(lambda dt, text=info_text: self.update_ui(text), 0)
                        
                        await asyncio.sleep(1)
            except Exception as e:
                error_text = f"Connection Error: {e}\nReconnecting..."
                Clock.schedule_once(lambda dt, text=error_text: self.update_ui(text), 0)
                await asyncio.sleep(3)

    def update_ui(self, text):
        self.status_label.text = text

if __name__ == '__main__':
    SniperApp().run()
