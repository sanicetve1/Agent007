from agentic_app.memory import InMemoryConversationStore, MemoryTurn


def test_in_memory_store_append_and_get_turns():
    store = InMemoryConversationStore()
    store.append_turn("s1", MemoryTurn(user_input="u1", assistant_response="a1"))
    store.append_turn("s1", MemoryTurn(user_input="u2", assistant_response="a2"))

    turns = store.get_turns("s1")
    assert len(turns) == 2
    assert turns[0].user_input == "u1"
    assert turns[1].assistant_response == "a2"


def test_in_memory_store_clear_session():
    store = InMemoryConversationStore()
    store.append_turn("s1", MemoryTurn(user_input="u", assistant_response="a"))

    store.clear_session("s1")

    assert store.get_turns("s1") == []
