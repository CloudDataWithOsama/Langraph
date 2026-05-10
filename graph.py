from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph # type
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langchain_tavily import TavilySearch

load_dotenv()  # Ye command khud hi .env file se keys utha legi

model = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    temperature=0.7  # Ye AI ko thora natural aur conversational banayega
)

# Tools setup
tavily_tool = TavilySearch(max_results=2)
# Custom tools
def deposite_money(bankName: str, account: int, amount: float = 1500) -> dict:
    """
        Deposite money into an account.
        Args:
            bankName (str): Bank name.
            account (int): Account number.
            amount (float): Amount to be deposited.
        Returns:
            dict: Confirmation message.
    """
    print("---Deposite Money Tool Invoked---")
    return {"message": f"Successfull deposited {amount} into account {account} for {bankName}."}

tools = [tavily_tool, deposite_money]

agent = create_react_agent(model, tools)

# 1. State define karein (ye data nodes ke beech share hoga)
class GraphState(TypedDict):
    state: str

def router_function(state: GraphState):
    print("---Router Function Running---", state)
    if "am" in state["state"].lower():
        return "yes"
    return "no"


# 2. Nodes ke functions banayein
def node1(current_state: GraphState):
    print("---Node 1 Running---")
    input_text = current_state["state"]

    response = model.invoke(f"Please just correct this sentence if needed and just return the corrected one,  '{input_text}'.")
    response = response.content[0]['text']
    return {"state": response}

def node2(current_state: GraphState):
    input_text = current_state["state"]
    print("---Node 2 Running--- ", input_text)

    # response = model.invoke(input_text)
    response = agent.invoke({"messages": [("user", input_text)]})
    
    content = response["messages"][-1].content

    print("Node 2 LLM Response:", response.content)
    return {"state": content[0]['text']}

# 3. Graph build karein
workflow: StateGraph = StateGraph(GraphState)

# Nodes add karein
workflow.add_node("node1", node1)
workflow.add_node("node2", node2)

# Edges (Raaste) connect karein
workflow.add_edge(START, "node1")
workflow.add_conditional_edges("node1", router_function, {
        "yes": "node2", 
        "no": END
    })
# workflow.add_edge("node1", "node2")

workflow.add_edge("node2", END)

# Graph compile
graph: CompiledStateGraph = workflow.compile()


# 4. Run karein
while True:
    user_input = input("\nYou: ")
    if user_input.lower() in ["exit", "quit", "bye"]:
        print("AI: Goodbye!")
        break
    initial_input = {"state": user_input}
    result = graph.invoke(initial_input)

    print("\nAI:", result['state'])



# print(graph.get_graph().draw_mermaid())