# News Sources Management Interface

## Overview
A comprehensive web interface has been added to manage RSS news sources for the readability analysis system. The interface provides full CRUD (Create, Read, Update, Delete) operations with article count tracking.

## Features

### 🎯 Core Functionality
- **Add Sources**: Add new RSS feeds with optional name and description
- **View Sources**: List all configured sources with key metrics
- **Edit Sources**: Modify source details (URL, name, description)
- **Delete Sources**: Remove sources from monitoring
- **Article Counts**: Display number of articles stored per source
- **Activity Tracking**: Show last article fetch date for each source
- **🆕 Immediate Scanning**: New and edited sources are scanned instantly for articles

### 🌐 Web Interface
- **Modern UI**: Bootstrap-based responsive design
- **Navigation**: Integrated navigation bar across all pages
- **Icons**: Font Awesome icons for better UX
- **Modals**: Clean modal dialogs for edit/delete operations
- **Form Validation**: Client and server-side validation
- **🆕 User Feedback**: Toast notifications show when sources are being scanned
- **🆕 Real-time Updates**: Visual indicators for scanning status

## Access the Interface

1. **Start the services**: `docker-compose up -d --build`
2. **Open browser**: Navigate to `http://localhost:4912`
3. **Default route**: The root URL now redirects to `/sources`

## API Endpoints

### Web Routes
- `GET /sources` - Main sources management page
- `POST /sources/add` - Add new source
- `POST /sources/edit/:id` - Update existing source
- `POST /sources/delete/:id` - Delete source

### Legacy Routes (still available)
- `GET /add-url?url=<rss_url>` - Simple URL addition (API only)
- `GET /daily` - Daily readability report
- `GET /graph` - Graph visualization
- `GET /export` - Data export

## Database Schema

### `urls` Collection
Sources are stored with enhanced metadata:
```javascript
{
  _id: ObjectId,
  url: String,           // RSS feed URL
  name: String,          // Display name (auto-generated from hostname if not provided)
  description: String,   // Optional description
  dateAdded: Date,       // When source was added
  lastModified: Date     // Last update timestamp
}
```

### Article Counting
- Real-time article counts per source
- Uses aggregation on `documents` collection
- Tracks articles by `origin` field

## Usage Examples

### Adding a Source
1. Navigate to `/sources`
2. Fill in the "Add New Source" form:
   - **URL**: RSS feed URL (required)
   - **Name**: Display name (optional - auto-generates from URL)
   - **Description**: Optional description
3. Click "Add Source"
4. **🆕 Immediate Scan**: The source will be scanned immediately for articles
5. **🆕 Feedback**: A notification will show the scanning progress

### Managing Sources
- **Edit**: Click edit button, modify in modal, save
- **Delete**: Click delete button, confirm in modal
- **View Articles**: Article count shows total stored articles
- **🆕 Auto-Rescan**: Edited sources are automatically re-scanned for new content
- **🆕 Change Detection**: URL changes trigger immediate re-scanning

## Technical Implementation

### Backend Changes
- Added express middleware for form parsing
- New source management functions in `src/index.js`
- Enhanced error handling and validation
- MongoDB ObjectId handling for updates/deletes
- **🆕 Single Source Scanning**: Extracted scanning logic for individual sources
- **🆕 Immediate Processing**: New/edited sources trigger instant article collection
- **🆕 Background Scanning**: Non-blocking scan execution with detailed logging

### Frontend Changes
- New EJS template: `src/views/pages/sources.ejs`
- Updated layout with navigation: `src/views/layouts/layout.ejs`
- Font Awesome icons added globally
- Bootstrap modals for edit/delete operations
- **🆕 Toast Notifications**: User feedback for scanning operations
- **🆕 Visual Indicators**: Clear messaging about automatic scanning
- **🆕 Form Enhancements**: Helpful text explaining immediate scanning behavior

### Route Updates
- Root route (`/`) now redirects to `/sources`
- Scan functionality moved to `/scan`
- All existing routes preserved

## Security & Validation
- URL format validation
- Server-side input validation
- XSS protection via EJS escaping
- Required field validation

## Navigation Structure
```
News Analysis
├── Sources (/)
├── Daily Report (/daily)
├── Graph View (/graph)
└── Export (/export)
```

## Quick Start

1. **Access the interface**: http://localhost:4912
2. **Add your first source**: Use the form to add an RSS feed
3. **🆕 Instant Results**: Watch the scanning notification appear and articles get processed immediately
4. **Monitor articles**: Watch article counts grow as the system processes feeds
5. **Manage sources**: Edit names, descriptions, or remove unused sources

## 🆕 New Feature Highlights

### Immediate Scanning
- **No Waiting**: Sources are scanned immediately upon addition or editing
- **Background Processing**: Scanning happens without blocking the interface
- **Visual Feedback**: Toast notifications keep you informed of scanning progress
- **Detailed Logging**: Server logs show scan results and article processing counts
- **Smart Detection**: URL changes trigger automatic re-scanning

### How It Works
1. **Add/Edit Source** → Triggers `scanSingleSource()` function
2. **RSS Parsing** → Fetches and parses the RSS feed
3. **Article Processing** → Each article sent to readability analysis service
4. **Database Storage** → Articles saved with readability metrics
5. **User Feedback** → Console logs and toast notifications show progress

The interface integrates seamlessly with the existing readability analysis pipeline, providing a user-friendly way to manage your news sources with instant feedback and immediate article collection.
