from langchain_core.messages import HumanMessage
from agent.graph import agent_graph

def chat(user_input: str, history: list = []):
    history.append(HumanMessage(content=user_input))
    result = agent_graph.invoke({
        "messages": history,
        "customer_name": None,
        "last_tool_called": None
    })
    response = result["messages"][-1].content
    print(f"Agent: {response}\n")
    return result["messages"]

# Test 1 — product question
history = chat("Do you have anything with pistachios?")

# Test 2 — availability
history = chat("Is the large size available?", history)

# Test 3 — order
history = chat("I'd like to order one. My name is Sara.", history)