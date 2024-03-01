#!/usr/bin/env python3
"""
The TulipAgent core
Process:
1) Initialize agent with a vector store
2) Take user request
3) Check for suitable functions, note that this is not tracked in message history
4) Run prompt with suitable tools
5) If applicable, run tool calls
6) Return response
"""
import json
import logging

from openai import OpenAI, OpenAIError

from prompts import TULIP_PROMPT
from tool_library import ToolLibrary


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class TulipAgent:
    def __init__(
        self,
        model: str = "gpt-4-0125-preview",
        temperature: float = 0.0,
        tool_library: ToolLibrary = None,
        top_k_functions: int = 3,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.instructions = TULIP_PROMPT
        self.tool_library = tool_library
        self.top_k_functions = top_k_functions
        self.openai_client = OpenAI()

        self.messages = []
        if self.instructions:
            self.messages.append({"role": "system", "content": self.instructions})

        self.search_tools_description = {
            "type": "function",
            "function": {
                "name": "search_tools",
                "description": ("Search for tools in your tool library."),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action_descriptions": {
                            "type": "array",
                            "items": {
                                "type": "string",
                            },
                            "description": "A list of textual description for the actions you want to execute.",
                        },
                    },
                    "required": ["problem_description"],
                },
            },
        }

    def search_tools(self, action_descriptions: str):
        json_res, hash_res = [], []
        for action_description in action_descriptions:
            res = self.tool_library.search(
                problem_description=action_description, top_k=self.top_k_functions
            )["documents"][0]
            json_res_ = [json.loads(e) for e in res if e not in hash_res]
            hash_res.extend(res)
            logging.info(
                f"Functions for `{action_description}`: {json.dumps(json_res_)}"
            )
            json_res.extend(json_res_)
        return json_res

    def __get_response(
        self,
        msgs: list[dict[str, str]],
        model: str = None,
        temperature: float = None,
        tools: list = None,
        tool_choice: str = "auto",
    ):
        response = None
        while not response:
            try:
                response = self.openai_client.chat.completions.create(
                    model=model if model else self.model,
                    messages=msgs,
                    tools=tools,
                    temperature=temperature if temperature else self.temperature,
                    tool_choice=tool_choice if tools else "none",
                )
            except OpenAIError as e:
                logger.error(e)
        return response

    def query(
        self,
        prompt: str,
    ) -> str:
        logging.info(f"Query: {prompt}")

        # Analyze user prompt
        self.messages.append(
            {
                "role": "user",
                "content": (
                    f"Considering the following user request, what are the necessary atomic actions "
                    f"you need to execute?\n `{prompt}`\nReturn a numbered list of steps."
                ),
            }
        )
        actions_response = self.__get_response(
            msgs=self.messages,
            tool_choice="none",
            tools=[self.search_tools_description],
        )
        actions_response_message = actions_response.choices[0].message
        self.messages.append(actions_response_message)
        logging.info(f"{actions_response_message=}")

        # Search for suitable functions
        self.messages.append(
            {
                "role": "user",
                "content": "Now search for appropriate tools for each of these steps.",
            }
        )
        function_response = self.__get_response(
            msgs=self.messages,
            tools=[self.search_tools_description],
            tool_choice={"type": "function", "function": {"name": "search_tools"}},
        )
        response_message = function_response.choices[0].message
        tool_calls = response_message.tool_calls
        self.messages.append(response_message)
        assert (
            lntc := len(tool_calls)
        ) == 1, f"Not exactly one tool search executed, but {lntc}."

        tools = []
        for tool_call in tool_calls:
            func = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            assert func == "search_tools", f"Unexpected tool call: {func}"

            # search tulip for function with args
            logging.info(f"Tool search for: {str(args)}")
            tools_ = self.search_tools(**args)
            logging.info(f"Tools found: {str(tools_)}")
            tools.extend(tools_)
            self.messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": func,
                    "content": "Successfully provided suitable tools.",
                }
            )

        # Run with suitable tools
        self.messages.append(
            {
                "role": "user",
                "content": (
                    f"Now use the tools to fulfill the user request. "
                    f"Adhere exactly to the following steps:\n"
                    f"{actions_response_message.content}\n"
                    f"Execute the tool calls one at a time."
                ),
            }
        )
        response = self.__get_response(
            msgs=self.messages,
            tools=tools,
            tool_choice="auto",
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        while tool_calls:
            self.messages.append(response_message)

            for tool_call in tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                function_response = self.tool_library.execute(
                    function_name=func_name, function_args=func_args
                )
                self.messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": func_name,
                        "content": str(function_response),
                    }
                )
                logger.info(
                    f"Function {func_name} returned `{str(function_response)}` for arguments {func_args}."
                )

            response = self.__get_response(
                msgs=self.messages,
                tools=tools,
                tool_choice="auto",
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
        self.messages.append(response_message)
        return response_message.content
