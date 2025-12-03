from typing import List

from agents.fairy.fairy_guild_agent import graph_builder as guild_builder
from agents.fairy.fairy_dungeon_agent import graph_builder as dungeon_builder
from agents.fairy.fairy_interaction_agent import graph_builder as interaction_builder
from langgraph.checkpoint.memory import MemorySaver
from agents.fairy.util import add_human_message

from core.game_dto.DungeonPlayerData import DungeonPlayerData

dungeon_memory = MemorySaver()
dungeon_graph = dungeon_builder.compile(dungeon_memory)
async def fairy_dungeon_talk(
    dungeon_player: DungeonPlayerData,
    question: str,
    targetMonsterIds: List[int],
    nextRoomId: int,
) -> str:
    playerId = dungeon_player.playerId
    config = {
        "configurable": {
            "thread_id": playerId,
            "playerId": playerId,
            "targetMonsterIds": targetMonsterIds,
            "nextRoomId": nextRoomId,
        }
    }
    print("여기 왔다")
    response = await dungeon_graph.ainvoke(
        {
            "messages": [add_human_message(content=question)],
            "dungenon_player": dungeon_player,
        },
        config=config,
    )
    messages = response["messages"]
    print(messages)

    result = messages[-1].content
    print(result)
    return result


guild_memory = MemorySaver()
guild_graph = guild_builder.compile(guild_memory)
async def fairy_guild_talk(
    playerId: int,
    question: str,
    heroine_id: int,
    affection:int,
    memory_progress: int,
    sanity:int,
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

    response = await guild_graph.ainvoke(
        {"messages": [add_human_message(question)]},
        config=config,
    )
    messages = response["messages"]
    print(messages)

    result = messages[-1].content
    print(result)
    return result

interaction_graph = interaction_builder.compile()
def fairy_interaction(dungeon_player: DungeonPlayerData, question: str) -> dict:

    myInventory = dungeon_player.inventory
    response = interaction_graph.invoke(
        {"messages": [add_human_message(question)], "inventory": myInventory}
    )
    return {
        "useItemId": response["useItemId"],
        "roomLight": response["roomLight"],
        "isCheckNextRoom": response["isCheckNextRoom"],
    }
