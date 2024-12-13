# ChatBloom Caribbean - Gender News Analysis System

A React-based web application for analyzing and providing insights on gender-related news articles from Caribbean countries.

## Live Demo
Visit the live application at: https://uwi-msbm-gender-chatbot-frontend-1.onrender.com/

## Prerequisites

- Node.js (v18.17.0 or higher)
- npm (comes with Node.js)
- Python 3.8+ (for the backend API)
- MongoDB instance
- AstraDB account
- OpenAI API key

## Project Structure

```
chatbloom-caribbean/
├── src/                    # Source files
│   ├── components/         # React components
│   ├── pages/             # Page components
│   └── server/            # Python backend
├── public/                # Static files
└── dist/                  # Production build output
```

## Local Development Setup

### Frontend Setup

1. Clone the repository:
```bash
git clone [repository-url]
cd chatbloom-caribbean
```

2. Create a `.env` file in the root directory for the frontend:
```env
VITE_API_URL=http://localhost:8000
```

3. Install dependencies:
```bash
npm install
```

4. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:8080`

### Backend Setup

1. Create and activate a Python virtual environment:
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

2. Install Python dependencies:
```bash
cd src/server
pip install -r requirements.txt
```

3. Create a `.env` file in the `src/server` directory with the following variables:
```env
# API Configuration
APP_ENV=development
APP_PORT=8000
APP_HOST=127.0.0.1

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Database Configuration
MONGODB_URI=your_mongodb_uri
ASTRA_DB_ID=your_astra_db_id
ASTRA_DB_REGION=your_astra_db_region
ASTRA_DB_APPLICATION_TOKEN=your_astra_token

# Logging Configuration
LOG_LEVEL=INFO
```

4. Start the backend server:
```bash
# Make sure you're in the root directory
python -m src.server.api.main
```

The backend API will be available at `http://localhost:8000`

## Available Scripts

- `npm run dev` - Start the development server
- `npm run build` - Create a production build
- `npm run preview` - Preview the production build locally
- `npm run lint` - Run ESLint for code quality

## Features

- Interactive chat interface for querying news articles
- Keyword-based search functionality
- Gender-focused news article analysis
- Real-time response streaming

## Tech Stack

- Frontend:
  - React
  - TypeScript
  - Vite
  - TailwindCSS
  - Shadcn/ui
  - Framer Motion

- Backend:
  - FastAPI
  - MongoDB
  - AstraDB
  - OpenAI

## Troubleshooting

### Common Issues

1. **Environment Variables Error**:
   - Make sure all environment variables are properly set in the `.env` files
   - The backend `.env` file should be in the `src/server` directory
   - Check that the variable names match exactly as shown above

2. **MongoDB Connection Error**:
   - Ensure MongoDB is running locally or your MongoDB Atlas connection string is correct
   - Check if the MongoDB URI includes the database name

3. **AstraDB Connection Error**:
   - Verify your AstraDB credentials
   - Make sure the database and keyspace exist

4. **OpenAI API Error**:
   - Verify your OpenAI API key is valid
   - Check if you have sufficient credits

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
