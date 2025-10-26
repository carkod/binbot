# Mermaid diagram

---
config:
  layout: dagre
  theme: redux
---
flowchart TD
 subgraph Databases["Databases"]
        n1["api_db"]
        Mongo[("Times Series")]
  end
 subgraph Binbot["Binbot"]
        RestAPI["Rest API"]
        Streaming["Streaming Service<br>(Market updates)"]
        Cronjobs["Cronjobs"]
  end
 subgraph Binquant["Binquant"]
        Producer["Producer"]
        Consumer["Consumer<br>(technicals, AI)"]
        Kafka["Kafka server"]
        Autotrade["Autotrade<br> autotrade_consumer.py"]
  end
 subgraph Client["External (internet)"]
        Websockets["Binance Websockets"]
        Terminal["Dashboard<br /> (Vite/React app)"]
        Telegram["Telegram bot"]
        Binance["Binance API"]
  end
    n1 -- Feeds --> RestAPI
    Mongo -- Candles, ADR --> RestAPI
    RestAPI -- Feeds --> Terminal & Producer
    Websockets -- "Real-time data" --> Producer
    Producer -- Structured data --> Kafka
    Producer -- Structured candles --> Mongo
    Kafka -- Queue --> Consumer
    Cronjobs -- Update, create, clean time series data --> RestAPI
    Streaming -- Update Bots --> RestAPI
    Binance -- Feeds --> RestAPI
    RestAPI -- Store --> n1 & Mongo
    Consumer -- Signals --> Telegram
    Consumer -- Signals<br>(automated trading) --> Autotrade
    n1@{ icon: "azure:azure-database-postgresql-server", pos: "b"}
    style Websockets fill:#FFD600
    style Terminal fill:#FF6D00,color:#FFFFFF
    style Telegram fill:#2962FF,color:#FFFFFF
    style Binance fill:#FFD600
