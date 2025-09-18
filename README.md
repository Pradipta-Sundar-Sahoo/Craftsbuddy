# CraftBuddy Telegram Bot

A production-ready Telegram bot that helps artisan sellers upload products with AI assistance for generating descriptions and specifications.

## Features

- **Product Upload Flow**: Guided process for uploading product images, names, prices, and specifications
- **AI-Powered Assistance**: Uses Google's Gemini AI for:
  - Product specification question generation
  - Product description generation
  - Image analysis and price standardization
- **Smart Specification Questions**: Dynamically generates the 5 most relevant questions based on product type
- **Session Management**: Handles user sessions with timeout and context preservation
- **Production Ready**: Proper logging, error handling, and modular architecture

## Project Structure

```
CraftsBudyy/
├── src/
│   ├── config/          # Configuration management
│   ├── models/          # Data models (Session, Product)
│   ├── services/        # Business logic services
│   ├── handlers/        # Message and callback handlers
│   ├── utils/           # Utility functions
│   ├── constants/       # Constants and specifications
│   ├── bot.py          # Main bot class
│   └── main.py         # Entry point
├── main.py             # Top-level entry point
├── requirements.txt    # Python dependencies
├── env.template        # Environment variables template
└── README.md          # This file
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd CraftsBudyy
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp env.template .env
   # Edit .env with your actual API keys
   ```

4. **Set up environment variables**:
   - `TELEGRAM_BOT_TOKEN`: Get from [@BotFather](https://t.me/BotFather)
   - `GEMINI_API_KEY`: Get from [Google AI Studio](https://aistudio.google.com/) (optional)

## Usage

### Running the Bot

```bash
python main.py
```

Or using the src entry point:

```bash
python src/main.py
```

### Bot Commands

- `/start` - Initialize the bot and show welcome message
- `/restart` - Reset current session and start over
- `/status` - Show current session status (for debugging)

### Product Upload Flow

1. User clicks "Upload a Product"
2. Bot requests product image
3. Bot asks for product name (optional)
4. Bot asks for product price (optional)
5. Bot generates 5 relevant specification questions based on product type
6. User answers questions (can skip any)
7. AI processes the information and generates description
8. Product is saved with all collected information

## Configuration

The bot uses environment variables for configuration:

- **Required**:
  - `TELEGRAM_BOT_TOKEN`: Telegram bot token

- **Optional**:
  - `GEMINI_API_KEY`: Google Gemini API key for AI features

### Configuration Options

See `src/config/settings.py` for all configurable options:

- Session timeout duration
- File storage directories  
- Polling timeout
- Logging configuration

## Architecture

### Core Components

1. **Bot Class** (`src/bot.py`): Main orchestrator
2. **Services** (`src/services/`): 
   - TelegramService: Telegram API interactions
   - GeminiService: AI functionality
   - ProductService: Product-related operations
3. **Handlers** (`src/handlers/`):
   - MessageHandler: Process text messages
   - CallbackHandler: Process button clicks
4. **Models** (`src/models/`):
   - Session: User session management
   - Product: Product data structure

### Key Features

- **Modular Design**: Separated concerns with clear boundaries
- **Error Handling**: Comprehensive error handling and logging
- **Session Management**: Automatic session timeout and cleanup
- **AI Integration**: Optional Gemini AI with graceful fallbacks
- **Production Ready**: Proper logging, configuration, and structure

## Development

### Code Structure

- Follow the existing modular pattern
- Add new features as services
- Use proper logging throughout
- Handle errors gracefully
- Write type hints

### Adding New Features

1. Create service classes in `src/services/`
2. Add handlers in `src/handlers/`
3. Update models if needed in `src/models/`
4. Configure in `src/config/settings.py`

## Deployment

### Docker (Recommended)

Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

### Systemd Service

Create `/etc/systemd/system/craftbuddy-bot.service`:
```ini
[Unit]
Description=CraftBuddy Telegram Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/CraftsBudyy
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Logging

Logs are written to:
- Console: All log levels
- `logs/bot.log`: Bot operations
- `logs/main.log`: Main application logs

## Data Storage

- **Images**: Saved to `product_images/` directory
- **Product Data**: Saved as JSON files in `product_data/` directory
- **Sessions**: In-memory (resets on restart)

## API Dependencies

- **Telegram Bot API**: Core bot functionality
- **Google Gemini API**: AI features (optional)

## License

[Add your license information here]

## Support

[Add support/contact information here]
