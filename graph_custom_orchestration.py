from typing import Literal, TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
# from langgraph.graph import MessagesState
from langgraph.graph.state import CompiledStateGraph # type
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, AIMessage
# from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from langchain_tavily import TavilySearch

load_dotenv()  # Ye command khud hi .env file se keys utha legi

model = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    temperature=0.7  # Ye AI ko thora natural aur conversational banayega
)

# State definition
class MessagesState(TypedDict): # Data Structure (Dict), Ye define karta hai ke humare graph ka state kaisa dikhega.
    messages: Annotated[list[AnyMessage], add_messages]

# Tools setup
tavily_tool = TavilySearch(max_results=2)
# Custom tools
def deposit_money(bankName: str, account: int=123444, amount: float = 1500) -> dict:
    """
        Deposit money into an account.
        Args:
            bankName (str): Bank name.
            account (int): Account number.
            amount (float): Amount to be deposited.
        Returns:
            dict: Confirmation message.
    """
    print("---Deposit Money Tool Invoked---")
    return {"status": "Success HO GYA", "balance": 5000}

tools = [tavily_tool, deposit_money]
model_with_tools = model.bind_tools(tools)

# 1. Router function
def router_function(state: MessagesState) -> Literal["tools", "__end__"]:
    """Ye faisla karta hai ke agla rasta kaunsa hai"""
    print("---Router Function Running---", state)
    last_message = state["messages"][-1]
    # Agar model ne tool call bheji hai, to 'tools' node par jao
    if last_message.tool_calls:
        return "tools"
    # Warna khatam kardo
    return END


# 2. Nodes
def node1(current_state: MessagesState) -> MessagesState:
    print("---Node 1 Running--- ", current_state)
    response = model_with_tools.invoke(current_state["messages"])
    return {"messages": [response]}


# 3. Graph build karein
workflow: StateGraph = StateGraph(MessagesState)

# Nodes add karein
workflow.add_node("node1", node1)
workflow.add_node("toolsNode", ToolNode(tools))



# Edges (Raaste) connection: ReAct Agent (Ressoning + Action)

workflow.add_edge(START, "node1")

workflow.add_conditional_edges(
    # Current node ke registered edges check honge.
    "node1", # Outgoing edges of current node (node1) is = toolsNode and END node.
    tools_condition,
    {"tools": "toolsNode", "__end__": END}, # outgoing edge of toolsNode is = node1
)

"""
Q: Real execution kis tarah hoti hai? 
A: Runtime pe LangGraph hamesha ye rule follow karta hai:
"Current node finish hui?
→ Ab dekho is node ke outgoing edges kya hain, 
"""

workflow.add_edge("toolsNode", "node1") 
# workflow se bahar nikalne k liye END node call hona chahiye jo is aumated workflow ko stop ya terminate kar dega. END node pe pahunchne ka matlab hai ke humne apna kaam successfully complete kar liya hai ya koi aisi condition aa gayi hai jahan se aage badhne ki zarurat nahi hai.
# Agar END node nahi hoga to workflow infinite loop me chala jayega, kyunki har baar "node1" se "toolsNode" pe jayega aur wapas "node1" pe aayega, bina kisi termination condition ke. END node isliye zaruri hai taaki hum apne workflow ko control kar sakein aur usy terminate kar sakein jab humara kaam complete ho jaye ya jab koi aisi situation aaye jahan se aage badhna zaruri na ho.

# Graph compile
graph: CompiledStateGraph = workflow.compile()

initial_input: MessagesState = None

# 4. Run karein
while True:
    user_input = input("\nYou: ")
    if user_input.lower() in ["exit", "quit", "bye"]:
        print("AI: Goodbye!")
        break

    if initial_input == None:
        initial_input: MessagesState = {"messages": [
            SystemMessage(content="Your name is 'Junior'. You are a helpful assistant."), 
            HumanMessage(content=user_input, name="Tahir")
            ]}
    else:
        initial_input["messages"].append(HumanMessage(content=user_input, name="Tahir"))
        
    result = graph.invoke(initial_input)
    initial_input = result  # Agle input ke liye state update kar do
    print("\nAI:", result)



print(graph.get_graph().draw_mermaid())