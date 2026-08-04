from typing import TypedDict

from langgraph.graph import START, END, StateGraph


class ProcessingStatus(TypedDict):
    raw_input: str
    processed: str
    output: str


def input_node(state: ProcessingStatus):
    clean_input = state["raw_input"].strip()
    return {
        "raw_input": clean_input,
    }


def process_node(state: ProcessingStatus):
    processed = state["raw_input"].upper()
    return {
        "processed": processed,
    }


def output_node(state: ProcessingStatus):
    return {
        "output": f"Result: {state['processed']}",
    }


graph = StateGraph(ProcessingStatus)
graph.add_node("input", input_node)
graph.add_node("process", process_node)
graph.add_node("output", output_node)
graph.add_edge(START, "input")
graph.add_edge("input", "process")
graph.add_edge("process", "output")
graph.add_edge("output", END)

app = graph.compile()

result = app.invoke({"raw_input": " hello world "})
print(result)
