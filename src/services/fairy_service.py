from typing import List, Optional

from agents.fairy.guild.fairy_guild_agent import graph_builder as guild_builder
from agents.fairy.dungeon.fairy_dungeon_agent import graph_builder as dungeon_builder
from agents.fairy.interaction.fairy_interaction_agent import (
    graph_builder as interaction_builder,
)
from langgraph.checkpoint.memory import MemorySaver
from agents.fairy.util import add_human_message
from agents.fairy.fairy_state import DungeonPlayerState

from core.game_dto.WeaponData import WeaponData
from core.game_dto.StatData import StatData
from agents.fairy.memory_messages import get_fairy_messages_dungeon

dungeon_graph = dungeon_builder.compile()
guild_graph = guild_builder.compile()

async def fairy_dungeon_talk(
    dungeon_player: DungeonPlayerState,
    question: str,
    target_monster_ids: List[int],
    next_room_ids: List[int],
) -> str:
    playerId = dungeon_player.playerId
    config = {
        "configurable": {
            "thread_id": playerId,
        }
    }
    memories = get_fairy_messages_dungeon(
        player_id=playerId, heroine_id=dungeon_player.heroineId, limit=4
    )
    response = await dungeon_graph.ainvoke(
        {
            "messages": memories + [add_human_message(content=question)],
            "dungenon_player": dungeon_player,
            "target_monster_ids": target_monster_ids,
            "player_id": playerId,
            "next_room_ids": next_room_ids,
        },
        config=config,
    )

    interrupts = response.get("__interrupt__")
    if interrupts:
        first = interrupts[0]
        msg = getattr(first, "value", first)
        return msg
    else:
        messages = response["messages"]
        print(messages)

        result = messages[-1].content
        print(result)
        return result






def fairy_guild_talk(
    playerId: int,
    question: str,
    heroine_id: int,
    affection: int,
    memory_progress: int,
    sanity: int,
) -> str:

    config = {
        "configurable": {
            "thread_id": playerId,
            "heroine_id": heroine_id,
            "memory_progress": memory_progress,
            "affection": affection,
            "sanity": sanity,
        }
    }

    response = guild_graph.ainvoke(
        {"messages": [add_human_message(question)]},
        config=config,
    )
    messages = response["messages"]
    print(messages)

    result = messages[-1].content
    print(result)
    return result


interaction_graph = interaction_builder.compile()


def fairy_interaction(
    player_id:str,
    heroine_id:int,
    stats:StatData,
    inventory: List[int],
    question: str,
    weapon: Optional[WeaponData],
) -> dict:
    memories = get_fairy_messages_dungeon(
            player_id=player_id, heroine_id=heroine_id, limit=4
    )
    myInventory = inventory
    response = interaction_graph.invoke(
        {   

            "messages": memories + [add_human_message(question)],
            "inventory": myInventory,
            "weapon": weapon,
            "stats":stats
        }
    )
    return {
        "useItemId": response["useItemId"],
        "roomLight": response["roomLight"],
    }
