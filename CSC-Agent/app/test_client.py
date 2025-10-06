import logging

from typing import Any
from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)


PUBLIC_AGENT_CARD_PATH = '/.well-known/agent.json'
EXTENDED_AGENT_CARD_PATH = '/agent/authenticatedExtendedCard'


async def main() -> None:
    # Configure logging to show INFO level messages
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  # Get a logger instance

    base_url = 'http://localhost:10006' # Ensure this matches your __main__.py port

    async with httpx.AsyncClient(timeout=60.0) as httpx_client:
        # Initialize A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
            # agent_card_path uses default, extended_agent_card_path also uses default
        )

        # Fetch Public Agent Card and Initialize Client
        final_agent_card_to_use: AgentCard | None = None

        try:
            logger.info(
                f'Attempting to fetch public agent card from: {base_url}{PUBLIC_AGENT_CARD_PATH}'
            )
            _public_card = (
                await resolver.get_agent_card()
            )  # Fetches from default public path
            logger.info('Successfully fetched public agent card:')
            logger.info(
                _public_card.model_dump_json(indent=2, exclude_none=True)
            )
            final_agent_card_to_use = _public_card
            logger.info(
                '\nUsing PUBLIC agent card for client initialization (default).'
            )

            if _public_card.supportsAuthenticatedExtendedCard:
                try:
                    logger.info(
                        '\nPublic card supports authenticated extended card. '
                        'Attempting to fetch from: '
                        f'{base_url}{EXTENDED_AGENT_CARD_PATH}'
                    )
                    auth_headers_dict = {
                        'Authorization': 'Bearer dummy-token-for-extended-card'
                    }
                    _extended_card = await resolver.get_agent_card(
                        relative_card_path=EXTENDED_AGENT_CARD_PATH,
                        http_kwargs={'headers': auth_headers_dict},
                    )
                    logger.info(
                        'Successfully fetched authenticated extended agent card:'
                    )
                    logger.info(
                        _extended_card.model_dump_json(
                            indent=2, exclude_none=True
                        )
                    )
                    final_agent_card_to_use = (
                        _extended_card  # Update to use the extended card
                    )
                    logger.info(
                        '\nUsing AUTHENTICATED EXTENDED agent card for client '
                        'initialization.'
                    )
                except Exception as e_extended:
                    logger.warning(
                        f'Failed to fetch extended agent card: {e_extended}. '
                        'Will proceed with public card.',
                        exc_info=True,
                    )
            elif (
                _public_card
            ):  # supportsAuthenticatedExtendedCard is False or None
                logger.info(
                    '\nPublic card does not indicate support for an extended card. Using public card.'
                )

        except Exception as e:
            logger.error(
                f'Critical error fetching public agent card: {e}', exc_info=True
            )
            raise RuntimeError(
                'Failed to fetch the public agent card. Cannot continue.'
            ) from e

        client = A2AClient(
            httpx_client=httpx_client, agent_card=final_agent_card_to_use
        )
        logger.info('A2AClient initialized.')

        # Test Case 1: Single turn query for general costing data (e.g., Brake Pad Set)
        send_message_payload_brake_pad: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': "Compare the prices for material U0000000139020000 in plant 3010?"}
                    # "Compare the prices for material U0000000139020000 in plant MBC Untertürkheim?"
                    # 'Provide me the similar parts for material A0000150400.',
                ],
                'messageId': uuid4().hex,
            },
        }
        print("\nSending first message (costing data for Brake Pad Set)...\n")
        request_brake_pad = SendMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**send_message_payload_brake_pad)
        )
        response_brake_pad = await client.send_message(request_brake_pad)
        print(f"\nResponse for Brake Pad Set query:\n{response_brake_pad.model_dump(mode='json', exclude_none=True)}\n")

        # Test Case 2: Query for "Where are parts used" for Engine Block
        # send_message_payload_engine_block_usage: dict[str, Any] = {
        #     'message': {
        #         'role': 'user',
        #         'parts': [
        #             {'kind': 'text', 'text': 'Where are parts used for Engine Block (M276)?'}
        #         ],
        #         'messageId': uuid4().hex,
        #     },
        # }
        # print("\nSending message (Where are parts used for Engine Block)...\n")
        # request_engine_block_usage = SendMessageRequest(
        #     id=str(uuid4()), params=MessageSendParams(**send_message_payload_engine_block_usage)
        # )
        # response_engine_block_usage = await client.send_message(request_engine_block_usage)
        # print(f"\nResponse for 'Where parts are used' query:\n{response_engine_block_usage.model_dump(mode='json', exclude_none=True)}\n")

        # # Test Case 3: Query for "Similar parts" to Headlight Assembly (LED)
        # send_message_payload_similar_headlight: dict[str, Any] = {
        #     'message': {
        #         'role': 'user',
        #         'parts': [
        #             {'kind': 'text', 'text': 'Show me similar parts to Headlight Assembly (LED).'}
        #         ],
        #         'messageId': uuid4().hex,
        #     },
        # }
        # print("\nSending message (Similar parts to Headlight Assembly (LED))...\n")
        # request_similar_headlight = SendMessageRequest(
        #     id=str(uuid4()), params=MessageSendParams(**send_message_payload_similar_headlight)
        # )
        # response_similar_headlight = await client.send_message(request_similar_headlight)
        # print(f"\nResponse for 'Similar parts' query:\n{response_similar_headlight.model_dump(mode='json', exclude_none=True)}\n")

        # # Test Case 4: Query for "Cost comparison" for Alternator
        # send_message_payload_cost_comparison_alternator: dict[str, Any] = {
        #     'message': {
        #         'role': 'user',
        #         'parts': [
        #             {'kind': 'text', 'text': 'Perform a cost comparison for Alternator.'}
        #         ],
        #         'messageId': uuid4().hex,
        #     },
        # }
        # print("\nSending message (Cost comparison for Alternator)...\n")
        # request_cost_comparison_alternator = SendMessageRequest(
        #     id=str(uuid4()), params=MessageSendParams(**send_message_payload_cost_comparison_alternator)
        # )
        # response_cost_comparison_alternator = await client.send_message(request_cost_comparison_alternator)
        # print(f"\nResponse for 'Cost comparison' query:\n{response_cost_comparison_alternator.model_dump(mode='json', exclude_none=True)}\n")

        # # Test Case 5: Streaming request for another general costing data (e.g., Oil Filter)
        # streaming_send_message_payload_oil_filter: dict[str, Any] = {
        #     'message': {
        #         'role': 'user',
        #         'parts': [
        #             {'kind': 'text', 'text': 'Tell me the costing data for Oil Filter.'}
        #         ],
        #         'messageId': uuid4().hex,
        #     },
        # }

        # streaming_request_oil_filter = SendStreamingMessageRequest(
        #     id=str(uuid4()), params=MessageSendParams(**streaming_send_message_payload_oil_filter)
        # )

        # print("\nSending streaming message (costing data for Oil Filter)...\n")
        # stream_response_oil_filter = client.send_message_streaming(streaming_request_oil_filter)

        # async for chunk in stream_response_oil_filter:
        #     print(chunk.model_dump(mode='json', exclude_none=True))

        # # Additional Test Cases for new parts and queries
        # # Test Case 6: General costing for Fuel Pump (W204)
        # send_message_payload_fuel_pump: dict[str, Any] = {
        #     'message': {
        #         'role': 'user',
        #         'parts': [
        #             {'kind': 'text', 'text': 'What is the cost of Fuel Pump (W204)?'}
        #         ],
        #         'messageId': uuid4().hex,
        #     },
        # }
        # print("\nSending message (costing data for Fuel Pump (W204))...\n")
        # request_fuel_pump = SendMessageRequest(
        #     id=str(uuid4()), params=MessageSendParams(**send_message_payload_fuel_pump)
        # )
        # response_fuel_pump = await client.send_message(request_fuel_pump)
        # print(f"\nResponse for Fuel Pump query:\n{response_fuel_pump.model_dump(mode='json', exclude_none=True)}\n")

        # # Test Case 7: Parts usage for Dashboard Assembly
        # send_message_payload_dashboard_usage: dict[str, Any] = {
        #     'message': {
        #         'role': 'user',
        #         'parts': [
        #             {'kind': 'text', 'text': 'Where is the Dashboard Assembly used?'}
        #         ],
        #         'messageId': uuid4().hex,
        #     },
        # }
        # print("\nSending message (Where is Dashboard Assembly used)...\n")
        # request_dashboard_usage = SendMessageRequest(
        #     id=str(uuid4()), params=MessageSendParams(**send_message_payload_dashboard_usage)
        # )
        # response_dashboard_usage = await client.send_message(request_dashboard_usage)
        # print(f"\nResponse for 'Dashboard Assembly usage' query:\n{response_dashboard_usage.model_dump(mode='json', exclude_none=True)}\n")

        # # Test Case 8: Similar parts for Battery (AGM)
        # send_message_payload_similar_battery: dict[str, Any] = {
        #     'message': {
        #         'role': 'user',
        #         'parts': [
        #             {'kind': 'text', 'text': 'Are there similar parts to Battery (AGM)?'}
        #         ],
        #         'messageId': uuid4().hex,
        #     },
        # }
        # print("\nSending message (Similar parts to Battery (AGM))...\n")
        # request_similar_battery = SendMessageRequest(
        #     id=str(uuid4()), params=MessageSendParams(**send_message_payload_similar_battery)
        # )
        # response_similar_battery = await client.send_message(request_similar_battery)
        # print(f"\nResponse for 'Similar battery' query:\n{response_similar_battery.model_dump(mode='json', exclude_none=True)}\n")

        # # Test Case 9: Cost comparison for Fuel Injector
        # send_message_payload_cost_comparison_injector: dict[str, Any] = {
        #     'message': {
        #         'role': 'user',
        #         'parts': [
        #             {'kind': 'text', 'text': 'Compare the cost of Fuel Injector.'}
        #         ],
        #         'messageId': uuid4().hex,
        #     },
        # }
        # print("\nSending message (Cost comparison for Fuel Injector)...\n")
        # request_cost_comparison_injector = SendMessageRequest(
        #     id=str(uuid4()), params=MessageSendParams(**send_message_payload_cost_comparison_injector)
        # )
        # response_cost_comparison_injector = await client.send_message(request_cost_comparison_injector)
        # print(f"\nResponse for 'Cost comparison injector' query:\n{response_cost_comparison_injector.model_dump(mode='json', exclude_none=True)}\n")


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())

