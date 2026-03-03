# HuggingFace Daily Papers API Reference

## Endpoint

```
GET https://huggingface.co/api/daily_papers
```

## Response Format

Returns a JSON array of paper objects. Each object has the following structure:

```json
{
  "paper": {
    "id": "2603.02138",
    "title": "Paper Title",
    "authors": [
      {
        "_id": "...",
        "name": "Author Name",
        "hidden": false
      }
    ],
    "publishedAt": "2026-03-03T00:00:00.000Z",
    "submittedOnDailyAt": "2026-03-03T00:00:00.000Z",
    "summary": "Full abstract text...",
    "upvotes": 10,
    "discussionId": "...",
    "ai_summary": "AI-generated short summary",
    "ai_keywords": ["keyword1", "keyword2"],
    "thumbnail": "https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.02138.png",
    "numComments": 1,
    "githubRepo": "https://github.com/user/repo",
    "githubStars": 100,
    "projectPage": "https://project-page.com",
    "organization": {
      "_id": "...",
      "name": "org-name",
      "fullname": "Organization Name",
      "avatar": "https://..."
    }
  },
  "publishedAt": "2026-03-03T00:00:00.000Z",
  "title": "Paper Title",
  "summary": "Full abstract...",
  "thumbnail": "https://...",
  "numComments": 1,
  "submittedBy": {
    "_id": "...",
    "name": "submitter-username",
    "fullname": "Submitter Name",
    "type": "user"
  },
  "isAuthorParticipating": false
}
```

## Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `paper.id` | string | arXiv paper ID |
| `paper.title` | string | Paper title |
| `paper.summary` | string | Full abstract |
| `paper.ai_summary` | string | AI-generated short summary |
| `paper.ai_keywords` | array | Extracted keywords |
| `paper.upvotes` | number | Number of upvotes |
| `paper.authors` | array | List of authors |
| `paper.thumbnail` | string | Preview image URL |
| `paper.githubRepo` | string | GitHub URL (if available) |
| `paper.projectPage` | string | Project page URL (if available) |
| `paper.organization` | object | Associated organization |

## Rate Limits

No authentication required. Be respectful with request frequency.

## Paper Page URL

Each paper can be viewed at:
```
https://huggingface.co/papers/{paper_id}
```

Example: https://huggingface.co/papers/2603.02138
