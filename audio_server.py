import asyncio
import json
from aiohttp import web
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder

pcs = set()

class AudioTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self):
        super().__init__()
        self.track = None

    async def recv(self):
        frame = await self.track.recv()
        return frame

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    # Handle audio track
    audio_track = AudioTrack()
    
    @pc.on("track")
    def on_track(track):
        if track.kind == "audio":
            audio_track.track = track

    # Set remote description
    await pc.setRemoteDescription(offer)
    
    # Create answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        })
    )

async def on_shutdown(app):
    # Close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

async def init_app():
    app = web.Application()
    app.router.add_post("/offer", offer)
    app.on_shutdown.append(on_shutdown)
    return app

if __name__ == "__main__":
    app = init_app()
    web.run_app(app, host="0.0.0.0", port=8080)