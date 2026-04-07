# DataVerse AI Frontend

A modern Next.js 14 frontend for the DataVerse AI business intelligence platform.

## Features

- **Real-time Streaming**: Server-sent events for live query processing updates
- **Interactive Charts**: Plotly.js integration for rich data visualizations
- **Drag & Drop Upload**: Easy CSV file uploads with progress feedback
- **AI-Powered Analysis**: Natural language queries with intelligent responses
- **Responsive Design**: Modern UI built with Tailwind CSS

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Charts**: Plotly.js with React wrapper
- **Icons**: Lucide React

## Getting Started

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Backend Integration

The frontend expects a FastAPI backend running on `http://localhost:8001` with the following endpoints:

- `POST /upload` - File upload
- `GET /stream/{session_id}` - SSE streaming
- `POST /sessions/{session_id}/query` - Query processing
- `GET /sessions/{session_id}/queries` - Query history

## Project Structure

```
components/
├── ChatInterface.tsx      # Main chat interface
├── DatasetUploader.tsx    # File upload component
├── MessageBubble.tsx      # Message display component
├── ChartRenderer.tsx      # Plotly chart renderer

lib/
└── api.ts                 # API integration functions

store/
└── appStore.ts           # Zustand state management

types/
└── index.ts              # TypeScript type definitions
```

## Key Components

### ChatInterface
The main component that orchestrates the entire chat experience:
- Handles dataset uploads
- Manages real-time streaming
- Displays messages and charts
- Processes user queries

### DatasetUploader
Drag-and-drop file upload component with:
- File type validation (CSV only)
- Size limits (50MB max)
- Progress feedback
- Error handling

### ChartRenderer
Plotly.js integration for rendering interactive charts:
- Accepts JSON chart specifications
- Responsive design
- Interactive toolbars

### MessageBubble
Displays individual messages with support for:
- Text content
- Embedded charts
- AI narration summaries
- User/assistant differentiation