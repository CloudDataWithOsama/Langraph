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
    return {"status": "ok", "balance": 5000}

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

# def node2(current_state: MessagesState) -> MessagesState:
#     print("---Node 2 Running--- ", current_state)

#     # response = model.invoke(input_text)
#     call_response = model_with_tools.invoke(current_state["messages"])
    
#     print("Node 2: model_with_tools Response:", call_response)
#     return {"messages": [call_response]}


# 3. Graph build karein
workflow: StateGraph = StateGraph(MessagesState)

# Nodes add karein
workflow.add_node("node1", node1)
# workflow.add_node("node2", node2)
workflow.add_node("tools", ToolNode(tools))



# Edges (Raaste) connect karein
workflow.add_edge(START, "node1")
workflow.add_conditional_edges("node1", tools_condition)
workflow.add_edge("tools", END)


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



# print(graph.get_graph().draw_mermaid())