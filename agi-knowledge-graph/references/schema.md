# Knowledge Graph Schema

## Node Schema

### Paper Node
```json
{
  "id": "paper:2605.05191v1",
  "type": "paper",
  "title": "LongSeeker: Elastic Context Orchestration...",
  "arxiv_id": "2605.05191v1",
  "published": "2026-05-06T17:54:16Z",
  "source": "arxiv",
  "agi_score": 2.0,
  "categories": ["cs.AI"],
  "link": "http://arxiv.org/abs/2605.05191v1"
}
```

### Author Node
```json
{
  "id": "author:yijun_lu",
  "type": "author",
  "name": "Yijun Lu"
}
```

### Concept Node
```json
{
  "id": "concept:context_management",
  "type": "concept",
  "name": "context management",
  "frequency": 5
}
```

### Method Node
```json
{
  "id": "method:fine_tuning",
  "type": "method",
  "name": "fine-tuning",
  "frequency": 12
}
```

### Category Node
```json
{
  "id": "category:cs.AI",
  "type": "category",
  "name": "cs.AI"
}
```

## Edge Schema

### authored_by
```json
{
  "source": "paper:2605.05191v1",
  "target": "author:yijun_lu",
  "type": "authored_by"
}
```

### uses_method
```json
{
  "source": "paper:2605.05191v1",
  "target": "method:fine_tuning",
  "type": "uses_method",
  "confidence": 0.8
}
```

### related_concept
```json
{
  "source": "paper:2605.05191v1",
  "target": "concept:context_management",
  "type": "related_concept",
  "weight": 1.0
}
```

### categorized_as
```json
{
  "source": "paper:2605.05191v1",
  "target": "category:cs.AI",
  "type": "categorized_as"
}
```

### similar_to
```json
{
  "source": "paper:2605.05191v1",
  "target": "paper:2605.04200v1",
  "type": "similar_to",
  "weight": 0.75,
  "shared_concepts": 3
}
```
