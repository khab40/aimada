import asyncio
from contextlib import suppress
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.arena.engine import SimulationEngine
from app.schemas.arena import ArenaState
from app.websocket.manager import WebSocketManager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/arena")
async def arena_websocket(websocket: WebSocket) -> None:
    manager: WebSocketManager = websocket.app.state.websocket_manager
    simulation: SimulationEngine = websocket.app.state.simulation
    await manager.connect(websocket)

    receive_task = asyncio.create_task(websocket.receive_json())
    try:
        while True:
            state = await simulation.get_state()
            await manager.send_state(websocket, state)

            sleep_task = asyncio.create_task(asyncio.sleep(manager.stream_interval_seconds))
            done, pending = await asyncio.wait(
                {receive_task, sleep_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            if receive_task in done:
                if receive_task.cancelled():
                    break
                try:
                    message = receive_task.result()
                except (asyncio.CancelledError, WebSocketDisconnect, RuntimeError):
                    break
                updated_state = await _handle_client_message(message, simulation)
                if updated_state is not None:
                    await manager.broadcast_state(updated_state)
                receive_task = asyncio.create_task(websocket.receive_json())

            if sleep_task in pending:
                sleep_task.cancel()
                with suppress(asyncio.CancelledError):
                    await sleep_task
    except WebSocketDisconnect:
        pass
    except RuntimeError:
        pass
    finally:
        receive_task.cancel()
        with suppress(asyncio.CancelledError, WebSocketDisconnect, RuntimeError):
            await receive_task
        manager.disconnect(websocket)


async def _handle_client_message(message: dict[str, Any], simulation: SimulationEngine) -> ArenaState | None:
    message_type = message.get("type")
    if message_type == "arena_control":
        action = message.get("action")
        if action == "start":
            return await simulation.start()
        elif action == "pause":
            return await simulation.pause()
        elif action == "reset":
            return await simulation.reset()
    elif message_type == "launch_scenario":
        scenario = message.get("scenario")
        if isinstance(scenario, str):
            await simulation.start_scenario(scenario)
            return await simulation.get_state()
    return None
