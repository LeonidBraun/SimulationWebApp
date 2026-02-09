import asyncio
import pytest
from app_pkg.ws import UserConnectionManager


@pytest.mark.asyncio
async def test_broadcast_to_user():
    """Test broadcasting to a specific user"""
    mgr = UserConnectionManager()
    q1 = asyncio.Queue()
    ws1 = object()  # mock websocket

    async with mgr._lock:
        mgr.user_queues["alice"] = {ws1: q1}

    await mgr.broadcast_to_user("alice", {"x": 1})
    result = await q1.get()

    assert result == {"x": 1}


@pytest.mark.asyncio
async def test_broadcast_to_all_users():
    """Test broadcasting to all users"""
    mgr = UserConnectionManager()
    q1 = asyncio.Queue()
    q2 = asyncio.Queue()
    ws1 = object()
    ws2 = object()

    async with mgr._lock:
        mgr.user_queues["alice"] = {ws1: q1}
        mgr.user_queues["bob"] = {ws2: q2}

    await mgr.broadcast_to_all_users({"all": True})

    result1 = await q1.get()
    result2 = await q2.get()

    assert result1 == {"all": True}
    assert result2 == {"all": True}


@pytest.mark.asyncio
async def test_disconnect_removes_user():
    """Test that disconnect removes user when no connections remain"""
    mgr = UserConnectionManager()
    ws1 = object()
    q1 = asyncio.Queue()

    async with mgr._lock:
        mgr.user_queues["alice"] = {ws1: q1}
        mgr.ws_to_user[ws1] = "alice"

    await mgr.disconnect(ws1)

    assert "alice" not in mgr.user_queues
    assert ws1 not in mgr.ws_to_user


@pytest.mark.asyncio
async def test_broadcast_multiple_connections_same_user():
    """Test broadcasting to multiple connections of the same user"""
    mgr = UserConnectionManager()
    q1 = asyncio.Queue()
    q2 = asyncio.Queue()
    ws1 = object()
    ws2 = object()

    async with mgr._lock:
        mgr.user_queues["alice"] = {ws1: q1, ws2: q2}

    await mgr.broadcast_to_user("alice", {"msg": "hello"})

    r1 = await q1.get()
    r2 = await q2.get()

    assert r1 == {"msg": "hello"}
    assert r2 == {"msg": "hello"}
