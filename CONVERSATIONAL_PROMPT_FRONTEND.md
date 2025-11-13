# Conversational Prompt Manager - Frontend Implementation

## Overview

A complete frontend interface for managing conversational prompts that configure AI behavior in voice conversations. Users can create, edit, delete, and activate different prompt templates.

## Features Implemented

### 1. Prompt Management UI
- **Create New Prompts**: Users can create custom conversational prompts with names, greeting messages, and system instructions
- **Edit Existing Prompts**: Modify prompt content, names, and greeting messages
- **Delete Prompts**: Remove unwanted prompts with confirmation
- **Activate Prompts**: Set which prompt is currently active for conversations

### 2. User Interface Components

#### Prompt List View
- Shows all saved prompts with names and preview text
- Visual indicator for active prompt (green ring)
- Click to select and edit
- Delete button for each prompt

#### Prompt Editor
- Large text area for editing system prompt content
- Character and line counter
- Name field for prompt identification
- Greeting message text input
- Save/Create/Reset buttons with loading states

#### Status Messages
- Success/error notifications with auto-dismiss
- Visual feedback for all operations

### 3. Default Template

Includes a professional default template for new prompts:

```
You are an AI assistant in a voice call conversation.

IMPORTANT CONVERSATION RULES:
1. Keep responses SHORT (1-2 sentences maximum)
2. Respond naturally and conversationally
3. DO NOT ask multiple questions in one response
4. Wait for the user to speak - don't dominate the conversation
5. Be helpful but concise
6. If user says something brief or unclear, ask ONE clarifying question
7. Don't repeat the same type of response multiple times

Provide a SHORT, helpful response that continues the conversation naturally.
Remember: This is a voice call - keep it brief and conversational!
```

## API Endpoints Expected

The frontend expects these backend API endpoints (to be implemented):

### GET /api/prompts
Fetch all prompts for a user
```
Query params: user_id
Response: {
  success: boolean,
  data: ConversationalPrompt[]
}
```

### POST /api/prompts
Create a new prompt
```
Body: {
  name: string,
  system_prompt: string,
  greeting_message: string,
  user_id: string,
  is_active: boolean
}
Response: {
  success: boolean,
  data: ConversationalPrompt
}
```

### PUT /api/prompts/:id
Update an existing prompt
```
Body: {
  name: string,
  system_prompt: string,
  greeting_message: string
}
Response: {
  success: boolean,
  data: ConversationalPrompt
}
```

### POST /api/prompts/:id/activate
Set a prompt as active
```
Response: {
  success: boolean,
  data: ConversationalPrompt
}
```

### DELETE /api/prompts/:id
Delete a prompt
```
Response: {
  success: boolean
}
```

## Data Model

```typescript
interface ConversationalPrompt {
  id: string;
  name: string;
  system_prompt: string;
  greeting_message?: string;
  user_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
```

## Database Schema (PostgreSQL)

```sql
CREATE TABLE conversational_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    greeting_message TEXT,
    user_id TEXT NOT NULL,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_prompts_user_id ON conversational_prompts(user_id);
CREATE INDEX idx_prompts_active ON conversational_prompts(is_active);

-- Only one prompt can be active per user
CREATE UNIQUE INDEX idx_prompts_user_active
ON conversational_prompts(user_id)
WHERE is_active = true;
```

## Component Location

- **File**: `src/components/ConversationalPromptManager.tsx`
- **Integrated in**: `src/App.tsx` (added below Knowledge Base Manager)

## Usage

1. **Creating a Prompt**:
   - Click "New Prompt" button
   - Enter prompt name and optional greeting message
   - Write or paste system prompt
   - Click "Create Prompt"

2. **Editing a Prompt**:
   - Click on a prompt from the list
   - Modify name, greeting, or content
   - Click "Save Changes"

3. **Activating a Prompt**:
   - Select a prompt
   - Click "Set as Active" button
   - Active prompt is used for all new conversations

4. **Deleting a Prompt**:
   - Click trash icon on prompt card
   - Confirm deletion

## Styling & Design

- Clean, modern interface with gradient accents
- Responsive grid layout (3 columns on desktop)
- Clear visual hierarchy with icons
- Color-coded status messages (green for success, red for errors)
- Active prompt highlighted with green ring
- Loading states for async operations

## Tips Section

Includes helpful tips for users:
- Keep instructions clear and concise
- Define the AI's role and personality
- Specify response length and format preferences
- Include conversation guidelines
- Add domain-specific knowledge or constraints
- Test prompts to ensure desired behavior

## Integration Notes

1. The component uses `VITE_API_URL` environment variable for API base URL
2. Currently uses a demo user ID (`demo-user-123`) - should be replaced with actual authentication
3. All API calls include `ngrok-skip-browser-warning` header for development
4. Error handling with user-friendly messages
5. Auto-refresh after CRUD operations

## Next Steps (Backend Required)

To make this functional, implement:

1. PostgreSQL database table for conversational_prompts
2. Backend API routes for CRUD operations
3. Integration with conversation generation service
4. Use active prompt and greeting message in AI response generation
5. Add user authentication and associate prompts with users

## Files Modified

- `src/components/ConversationalPromptManager.tsx` (NEW)
- `src/App.tsx` (updated to include new component)

## Testing

The project builds successfully with no TypeScript errors.

```bash
npm run build
# ✓ built in 3.49s
```

All frontend functionality is ready and waiting for backend API implementation.
