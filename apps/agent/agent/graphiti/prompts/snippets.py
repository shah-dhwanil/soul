"""
Copyright 2024, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from graphiti_core.utils.text_utils import MAX_SUMMARY_CHARS

summary_instructions = f"""Guidelines:
1. Output only facts, never explanations or mentions of limitations.
2. Use only the provided messages, entity, and entity context.
3. Be dense and entity-specific, under {MAX_SUMMARY_CHARS} characters. Keep names, roles, places, dates, counts, and temporal qualifiers that are explicitly supported.
4. State the content of what was said directly. Avoid "mentioned", "described", "stated", "reported", "noted", "discussed", "referenced", "indicated" unless the act of communication is itself the fact.
5. Start with the entity name or a direct fact, not "A", "An", "The", or "This is" (unless part of the name).

BAD: "The context shows John ordered pizza. Due to length constraints, other details are omitted."
GOOD: "John ordered pepperoni pizza from Mario's at 7:30 PM and had it delivered to the office."
"""
