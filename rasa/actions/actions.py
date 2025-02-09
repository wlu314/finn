import os
from typing import Any, Text, Dict, List
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import yfinance as yf

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, EventType

# Alpaca imports
from alpaca.trading.client import TradingClient
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.historical.corporate_actions import CorporateActionsClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.trading.stream import TradingStream
from alpaca.data.live.stock import StockDataStream

from alpaca.data.requests import (
    CorporateActionsRequest,
    StockBarsRequest,
    StockQuotesRequest,
    StockTradesRequest,
)
from alpaca.trading.requests import (
    ClosePositionRequest,
    GetAssetsRequest,
    GetOrdersRequest,
    LimitOrderRequest,
    MarketOrderRequest,
    StopLimitOrderRequest,
    StopLossRequest,
    StopOrderRequest,
    TakeProfitRequest,
    TrailingStopOrderRequest,
)
from alpaca.trading.enums import (
    AssetExchange,
    AssetStatus,
    OrderClass,
    OrderSide,
    OrderType,
    QueryOrderStatus,
    TimeInForce,
)
import nest_asyncio
nest_asyncio.apply()


import os
from openai import OpenAI
client = OpenAI(api_key="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")

def analyze_stock_ticker(query: str):
    """
    Sends the user query to GPT-3.5-turbo and instructs it to return
    only the stock ticker in curly braces (e.g., {AAPL}).
    """
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        # Setting temperature=0 can help ensure more consistent, 
        # deterministic responses when parsing.
        temperature=1,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful financial assistant. The user will give you a query, which may or may not "
                    "contain references to companies or ticker symbols You will inference the ticker symbol that the user wants to invest in"
                    "Respond *only* in the format `{TICKER}` with no extra text."
                    "The ticker symbol should be uppercase letters only when returned."
                )
            },
            {
                "role": "user",
                "content": query
            }
        ]
    )
    
    return completion.choices[0].message.content


## validate stock
def validate_symbol(symbol: str) -> bool:
    try:
        stock = yf.Ticker(symbol)
        return stock.info.get('regularMarketPrice') is not None
    except:
        return False
    

# Connect to trade client
def get_alpaca_trade_client() -> TradingClient:
    # Load environment variables from a .env file in the current directory
    load_dotenv()  

    api_key = os.getenv("APCA_API_KEY_ID")
    secret_key = os.getenv("APCA_API_SECRET_KEY")

    if not api_key or not secret_key:
        raise ValueError("Alpaca API credentials missing. Check your .env file or environment variables.")

    paper = True  # False if using a live account
    return TradingClient(api_key=api_key, secret_key=secret_key, paper=paper)

# 2) ACTION: Place Market Order (either by qty or notional)
# class ActionPlaceMarketOrder(Action):
#     def name(self) -> Text:
#         return "action_place_market_order"

#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[EventType]:
        
#         symbol = tracker.get_slot("symbol")
#         side = tracker.get_slot("side") or "BUY"  # default
#         qty = tracker.get_slot("qty")  # could be float
#         notional = tracker.get_slot("notional")  # user might specify dollar amount
#         time_in_force = tracker.get_slot("time_in_force") or "DAY"


#         if not validate_symbol(symbol):
#             inferred_symbol = analyze_stock_ticker(symbol)
#             if validate_symbol(inferred_symbol):
#                 symbol = inferred_symbol
#                 dispatcher.utter_message(text=f"I inferred that you meant {symbol}. Using this symbol.")
#             else:
#                 dispatcher.utter_message(text=f"{symbol} is not a valid stock ticker. Please enter a correct one.")
#                 return []

#         if not qty and not notional:
#             dispatcher.utter_message(text="Please specify the number of shares or the total dollar amount.")
#             return []
        
#         try:
#             trade_client = get_alpaca_trade_client()
            
#             market_req = MarketOrderRequest(
#                 symbol=symbol,
#                 side=OrderSide(side.upper()),
#                 time_in_force=TimeInForce(time_in_force.upper()),
#                 qty=float(qty) if qty else None,
#                 notional=float(notional) if notional else None
#             )

#             dispatcher.utter_message(text=f"Placing a market order for {qty if qty else '$' + str(notional)} of {symbol}...")

#             # Submit the order
#             res = trade_client.submit_order(market_req)
#             dispatcher.utter_message(text=f"Market order placed successfully: {res}")
#         except Exception as e:
#             dispatcher.utter_message(text=f"Error placing market order: {str(e)}")

#         return []

class ActionPlaceMarketOrder(Action):
    def name(self) -> Text:
        return "action_place_market_order"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:

        # Only capture these three slots from RASA
        symbol = tracker.get_slot("symbol")
        side = tracker.get_slot("side") or "BUY"  
        qty = tracker.get_slot("qty")

        if not symbol or not qty:
            dispatcher.utter_message(
                text="Missing symbol or quantity. Please provide both."
            )
            return []

        # Validate symbol (optional step)
        if not validate_symbol(symbol):
            dispatcher.utter_message(
                text=f"{symbol} is not a valid stock ticker. Please try again."
            )
            return []

        try:
            trade_client = get_alpaca_trade_client()

            # Hard-code type = MARKET and time_in_force = DAY
            market_req = MarketOrderRequest(
                symbol=symbol,
                side=OrderSide(side.upper()),
                qty=float(qty),
                type=OrderType.MARKET,           # Hard-coded
                time_in_force=TimeInForce.DAY    # Hard-coded
            )

            dispatcher.utter_message(
                text=f"Placing a MARKET order to {side.upper()} {qty} share(s) of {symbol}."
            )

            # Submit the order
            res = trade_client.submit_order(market_req)
            dispatcher.utter_message(
                text=f"Market order placed successfully: {res}"
            )

        except Exception as e:
            dispatcher.utter_message(
                text=f"Error placing market order: {str(e)}"
            )

        return []


# 3) ACTION: Place Limit Order
class ActionPlaceLimitOrder(Action):
    def name(self) -> Text:
        return "action_place_limit_order"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:

        symbol = tracker.get_slot("symbol")
        side = tracker.get_slot("side") or "BUY"
        qty = tracker.get_slot("qty")
        limit_price = tracker.get_slot("limit_price")
        time_in_force = tracker.get_slot("time_in_force") or "DAY"

        try:
            trade_client = get_alpaca_trade_client()
            
            limit_req = LimitOrderRequest(
                symbol=symbol,
                side=OrderSide(side.upper()),
                qty=float(qty),
                limit_price=float(limit_price),
                time_in_force=TimeInForce(time_in_force.upper()),
            )
            res = trade_client.submit_order(limit_req)
            dispatcher.utter_message(text=f"Limit order placed successfully: {res}")
        except Exception as e:
            dispatcher.utter_message(text=f"Error placing limit order: {str(e)}")

        return []


# 4) ACTION: Place Stop Order
class ActionPlaceStopOrder(Action):
    def name(self) -> Text:
        return "action_place_stop_order"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:

        symbol = tracker.get_slot("symbol")
        side = tracker.get_slot("side") or "BUY"
        qty = tracker.get_slot("qty")
        stop_price = tracker.get_slot("stop_price")
        time_in_force = tracker.get_slot("time_in_force") or "GTC"

        try:
            trade_client = get_alpaca_trade_client()
            
            stop_req = StopOrderRequest(
                symbol=symbol,
                side=OrderSide(side.upper()),
                qty=float(qty),
                stop_price=float(stop_price),
                time_in_force=TimeInForce(time_in_force.upper()),
            )
            res = trade_client.submit_order(stop_req)
            dispatcher.utter_message(text=f"Stop order placed: {res}")
        except Exception as e:
            dispatcher.utter_message(text=f"Error placing stop order: {str(e)}")

        return []


# 5) ACTION: Place Stop Limit Order
class ActionPlaceStopLimitOrder(Action):
    def name(self) -> Text:
        return "action_place_stop_limit_order"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:

        symbol = tracker.get_slot("symbol")
        side = tracker.get_slot("side") or "BUY"
        qty = tracker.get_slot("qty")
        stop_price = tracker.get_slot("stop_price")
        limit_price = tracker.get_slot("limit_price")
        time_in_force = tracker.get_slot("time_in_force") or "GTC"

        try:
            trade_client = get_alpaca_trade_client()
            
            stop_limit_req = StopLimitOrderRequest(
                symbol=symbol,
                side=OrderSide(side.upper()),
                qty=float(qty),
                stop_price=float(stop_price),
                limit_price=float(limit_price),
                time_in_force=TimeInForce(time_in_force.upper()),
            )
            res = trade_client.submit_order(stop_limit_req)
            dispatcher.utter_message(text=f"Stop limit order placed: {res}")
        except Exception as e:
            dispatcher.utter_message(text=f"Error placing stop limit order: {str(e)}")

        return []


# 6) ACTION: Place Bracket Order
class ActionPlaceBracketOrder(Action):
    def name(self) -> Text:
        return "action_place_bracket_order"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:

        symbol = tracker.get_slot("symbol")
        side = tracker.get_slot("side") or "BUY"
        qty = tracker.get_slot("qty")
        time_in_force = tracker.get_slot("time_in_force") or "DAY"
        take_profit_price = tracker.get_slot("take_profit_price")
        stop_loss_price = tracker.get_slot("stop_loss_price")

        try:
            trade_client = get_alpaca_trade_client()
            
            bracket_req = MarketOrderRequest(
                symbol=symbol,
                side=OrderSide(side.upper()),
                qty=float(qty),
                time_in_force=TimeInForce(time_in_force.upper()),
                order_class=OrderClass.BRACKET,
                take_profit=TakeProfitRequest(limit_price=float(take_profit_price)) if take_profit_price else None,
                stop_loss=StopLossRequest(stop_price=float(stop_loss_price)) if stop_loss_price else None
            )
            res = trade_client.submit_order(bracket_req)
            dispatcher.utter_message(text=f"Bracket order placed: {res}")
        except Exception as e:
            dispatcher.utter_message(text=f"Error placing bracket order: {str(e)}")

        return []


# 7) ACTION: Place OTO Order (Limit with stop_loss, for example)
class ActionPlaceOTOOrder(Action):
    def name(self) -> Text:
        return "action_place_oto_order"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:

        symbol = tracker.get_slot("symbol")
        side = tracker.get_slot("side") or "BUY"
        qty = tracker.get_slot("qty")
        limit_price = tracker.get_slot("limit_price")
        stop_loss_price = tracker.get_slot("stop_loss_price")
        time_in_force = tracker.get_slot("time_in_force") or "DAY"

        try:
            trade_client = get_alpaca_trade_client()
            
            oto_req = LimitOrderRequest(
                symbol=symbol,
                side=OrderSide(side.upper()),
                qty=float(qty),
                limit_price=float(limit_price),
                time_in_force=TimeInForce(time_in_force.upper()),
                order_class=OrderClass.OTO,
                stop_loss=StopLossRequest(stop_price=float(stop_loss_price)) if stop_loss_price else None
            )
            res = trade_client.submit_order(oto_req)
            dispatcher.utter_message(text=f"OTO order placed: {res}")
        except Exception as e:
            dispatcher.utter_message(text=f"Error placing OTO order: {str(e)}")

        return []


# 8) ACTION: Place OCO Order
class ActionPlaceOCOOrder(Action):
    def name(self) -> Text:
        return "action_place_oco_order"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:

        symbol = tracker.get_slot("symbol")
        side = tracker.get_slot("side") or "BUY"
        qty = tracker.get_slot("qty")
        limit_price = tracker.get_slot("limit_price")
        time_in_force = tracker.get_slot("time_in_force") or "DAY"

        try:
            trade_client = get_alpaca_trade_client()
            
            oco_req = LimitOrderRequest(
                symbol=symbol,
                side=OrderSide(side.upper()),
                qty=float(qty),
                limit_price=float(limit_price),
                time_in_force=TimeInForce(time_in_force.upper()),
                order_class=OrderClass.OCO
                # In practice, you often define a second price or stop, 
                # but the Alpaca Python API for OCO might need a more specialized request.
            )
            res = trade_client.submit_order(oco_req)
            dispatcher.utter_message(text=f"OCO order placed: {res}")
        except Exception as e:
            dispatcher.utter_message(text=f"Error placing OCO order: {str(e)}")

        return []


# 9) ACTION: Place Trailing Stop Order
class ActionPlaceTrailingStopOrder(Action):
    def name(self) -> Text:
        return "action_place_trailing_stop_order"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:

        symbol = tracker.get_slot("symbol")
        side = tracker.get_slot("side") or "SELL"  # trailing stops are often sells
        qty = tracker.get_slot("qty")
        time_in_force = tracker.get_slot("time_in_force") or "GTC"
        trail_price = tracker.get_slot("trail_price")
        trail_percent = tracker.get_slot("trail_percent")

        try:
            trade_client = get_alpaca_trade_client()
            
            trailing_req = TrailingStopOrderRequest(
                symbol=symbol,
                side=OrderSide(side.upper()),
                qty=float(qty),
                time_in_force=TimeInForce(time_in_force.upper()),
            )
            if trail_percent:
                trailing_req.trail_percent = float(trail_percent)
            elif trail_price:
                trailing_req.trail_price = float(trail_price)

            res = trade_client.submit_order(trailing_req)
            dispatcher.utter_message(text=f"Trailing stop order placed: {res}")
        except Exception as e:
            dispatcher.utter_message(text=f"Error placing trailing stop order: {str(e)}")

        return []


# 10) ACTION: Get Orders (All or by Symbol, maybe status)
class ActionGetOrders(Action):
    def name(self) -> Text:
        return "action_get_orders"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:

        symbol = tracker.get_slot("symbol")
        status_str = tracker.get_slot("order_status") or "ALL"  # user might say "open" or "closed"

        try:
            status_enum = QueryOrderStatus(status_str.upper())  # e.g. QueryOrderStatus.OPEN, ALL, etc.
            trade_client = get_alpaca_trade_client()
            
            if symbol:
                req = GetOrdersRequest(status=status_enum, symbols=[symbol])
            else:
                req = GetOrdersRequest(status=status_enum)
            orders = trade_client.get_orders(req)
            dispatcher.utter_message(text=f"Orders found:\n{orders}")
        except Exception as e:
            dispatcher.utter_message(text=f"Error retrieving orders: {str(e)}")

        return []


# 11) ACTION: Cancel All Open Orders
class ActionCancelAllOrders(Action):
    def name(self) -> Text:
        return "action_cancel_all_orders"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:
        try:
            trade_client = get_alpaca_trade_client()
            trade_client.cancel_orders()
            dispatcher.utter_message(text="All open orders have been canceled.")
        except Exception as e:
            dispatcher.utter_message(text=f"Error canceling orders: {str(e)}")

        return []


# 12) ACTION: Get Positions (All)
class ActionGetPositions(Action):
    def name(self) -> Text:
        return "action_get_positions"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:
        try:
            trade_client = get_alpaca_trade_client()
            positions = trade_client.get_all_positions()
            dispatcher.utter_message(text=f"Open positions:\n{positions}")
        except Exception as e:
            dispatcher.utter_message(text=f"Error retrieving positions: {str(e)}")

        return []


# 13) ACTION: Get Single Position by Symbol
class ActionGetPositionBySymbol(Action):
    def name(self) -> Text:
        return "action_get_position_by_symbol"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:

        symbol = tracker.get_slot("symbol")
        if not symbol:
            dispatcher.utter_message(text="Please specify a symbol to view a position.")
            return []

        try:
            trade_client = get_alpaca_trade_client()
            position = trade_client.get_open_position(symbol_or_asset_id=symbol)
            dispatcher.utter_message(text=f"Position for {symbol}: {position}")
        except Exception as e:
            dispatcher.utter_message(text=f"Error retrieving position: {str(e)}")

        return []


# 14) ACTION: Close Position
class ActionClosePosition(Action):
    def name(self) -> Text:
        return "action_close_position"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:

        symbol = tracker.get_slot("symbol")
        close_qty = tracker.get_slot("qty")  # user might specify how many shares to close

        if not symbol:
            dispatcher.utter_message(text="Please specify a symbol to close the position.")
            return []

        try:
            trade_client = get_alpaca_trade_client()
            if close_qty:
                close_req = ClosePositionRequest(qty=str(close_qty))
                res = trade_client.close_position(symbol_or_asset_id=symbol, close_options=close_req)
            else:
                # Closes entire position if no qty provided
                res = trade_client.close_position(symbol_or_asset_id=symbol)
            dispatcher.utter_message(text=f"Closed position for {symbol}: {res}")
        except Exception as e:
            dispatcher.utter_message(text=f"Error closing position: {str(e)}")

        return []

# Summarzing Orders
class ActionSummarizeOrder(Action):
    def name(self) -> Text:
        return "action_summarize_order"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:
        

        symbol = tracker.get_slot("symbol")
        qty = tracker.get_slot("qty")
        side = tracker.get_slot("side") or "BUY"

        # Validate the symbol (optional, but here if you want to ensure it’s real)
        if not validate_symbol(symbol):
            inferred_symbol = analyze_stock_ticker(symbol)
            if validate_symbol(inferred_symbol):
                symbol = inferred_symbol
                dispatcher.utter_message(
                    text=f"I inferred that you meant {symbol}. Using this symbol."
                )
            else:
                dispatcher.utter_message(
                    text=f"'{symbol}' is not a valid stock ticker. Please provide a valid one."
                )
                return []

        summary = (
            f"You are about to place a **{side.upper()} market order** "
            f"for **{qty} share(s) of {symbol}** "
            f"with **DAY** execution. Confirm?"
        )

        dispatcher.utter_message(text=summary)
        return []

    
class ActionSummarizeLimitOrder(Action):
    def name(self) -> Text:
        return "action_summarize_limit_order"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:

        symbol = tracker.get_slot("symbol")
        qty = tracker.get_slot("qty")
        limit_price = tracker.get_slot("limit_price")
        side = tracker.get_slot("side") or "BUY"
        time_in_force = tracker.get_slot("time_in_force") or "DAY"

        if not symbol or not limit_price:
            dispatcher.utter_message(text="I couldn't determine the stock symbol or limit price. Please provide these details.")
            return []

        summary = (f"You are about to place a limit order to {side} {qty} shares of {symbol} "
                   f"at ${limit_price} with {time_in_force} execution.")
        dispatcher.utter_message(text=summary)

        return []
    
class ActionSummarizeTrailingStop(Action):
    def name(self) -> Text:
        return "action_summarize_trailing_stop"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:

        symbol = tracker.get_slot("symbol")
        qty = tracker.get_slot("qty")
        trail_price = tracker.get_slot("trail_price")
        trail_percent = tracker.get_slot("trail_percent")
        side = tracker.get_slot("side") or "SELL"  # Default to SELL for trailing stops
        time_in_force = tracker.get_slot("time_in_force") or "GTC"

        if not symbol or (not trail_price and not trail_percent):
            dispatcher.utter_message(text="I couldn't determine the stock symbol or trailing stop parameters. Please provide these details.")
            return []

        summary = (f"You are about to place a trailing stop order to {side} {qty} shares of {symbol} "
                   f"with a {'trailing price of $' + str(trail_price) if trail_price else ''} "
                   f"{'and ' if trail_price and trail_percent else ''} "
                   f"{'trailing percentage of ' + str(trail_percent) + '%' if trail_percent else ''} "
                   f"using {time_in_force} execution.")

        dispatcher.utter_message(text=summary)
        return []

class ActionExecuteMarketOrder(Action):
    def name(self) -> Text:
        return "action_execute_market_order"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:

        symbol = tracker.get_slot("symbol")
        qty = tracker.get_slot("qty")
        side = tracker.get_slot("side") or "BUY"
        time_in_force = tracker.get_slot("time_in_force") or "DAY"

        if not symbol or not qty:
            dispatcher.utter_message(text="Error: Missing symbol or quantity for the market order.")
            return []

        try:
            trade_client = get_alpaca_trade_client()
            
            market_req = MarketOrderRequest(
                symbol=symbol,
                side=OrderSide(side.upper()),
                time_in_force=TimeInForce(time_in_force.upper()),
                qty=float(qty)
            )

            res = trade_client.submit_order(market_req)
            dispatcher.utter_message(text=f"Market order executed successfully: {res}")
        except Exception as e:
            dispatcher.utter_message(text=f"Error executing market order: {str(e)}")

        return []
