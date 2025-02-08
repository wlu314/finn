# Finn - AI Agent for Financial Markets  
## Interactive Trading with Alpaca API  

<img src="finn.png" alt="Finn AI" width="200">


## Overview  
**FinnBot.ai** is an AI-powered trading assistant designed to help users interact with financial markets through natural language queries. It processes user input using **RASA NLU**, converting it into actionable parameters for trading and market analysis. Finn currently integrates with the **Alpaca API**, enabling real-time market data retrieval, trade execution, and portfolio management. Future updates will expand support to additional trading platforms as time constraints allow.  

## _WHY_
Finn, short for "Financial Navigator," empowers retail investors by automating execution, optimizing trading efficiency, and providing AI-driven insights. With Finn, regular investors gain the analytical power of financial professionals, enabling them to make informed decisions simply by asking investment-related questions.


### 🔹 System Flow

1️⃣ User Request → "Place a market order for AAPL."

2️⃣ Rasa Detects Intent → Calls `action_place_market_order`.

3️⃣ Action Server Request → Rasa sends a request to rasa run actions.

4️⃣ Alpaca API Call → Action server fetches data from Alpaca API.

5️⃣ Response Sent → Processed result is returned to the user.


## Features  
- **Natural Language Trade Execution** – Place market, limit, and stop orders directly via chat.  
- **Portfolio Management** – View holdings, track performance, and manage open positions.  
- **Conversational AI** – Uses **RASA NLU** to understand trade intents and execute commands seamlessly.  

## Technology Stack  
- **Python** for backend development  
- **Alpaca API** for trading and market data access  
- **RASA NLU** for natural language processing and intent recognition  
- **React & Tailwind CSS** for the web-based UI (planned)  

## Future Enhancements  
- Integration with **other trading platforms** like Interactive Brokers, TD Ameritrade, and Binance  
- Advanced **AI-driven trading strategies** with reinforcement learning  

## Disclaimer  
This chatbot is intended for **educational and research purposes**. Trading stocks involves risk, and users should exercise due diligence before executing trades. The developer is **not responsible** for financial losses incurred.  
