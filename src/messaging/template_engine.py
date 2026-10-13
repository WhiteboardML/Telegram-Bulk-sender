import re
import random
from typing import Dict, List, Optional


class TemplateEngine:
    """Handles spintax evaluation, dynamic variable substitution, and message previewing."""

    @staticmethod
    def spin_text(text: str) -> str:
        """
        Recursively evaluate spintax format {option1|option2|...}.
        Supports nested spintax such as {Hello|{Hi|Hey} there}.
        """
        pattern = re.compile(r'\{([^{}]+)\}')
        max_iterations = 50  # Prevent infinite loops in malformed input
        iterations = 0

        while iterations < max_iterations:
            match = pattern.search(text)
            if not match:
                break
            
            # Extract options and choose randomly
            options = match.group(1).split('|')
            chosen = random.choice(options)
            text = text[:match.start()] + chosen + text[match.end():]
            iterations += 1

        return text

    @classmethod
    def render_template(cls, template: str, contact: Dict, default_name: str = "there") -> str:
        """
        Render a personalized message for a contact.
        Substitutes variables: {first_name}, {last_name}, {name}, {username}, {phone}, {user_id},
        and any custom fields present in the contact record, followed by spintax resolution.
        """
        # Resolve names with intelligent fallbacks
        full_name = contact.get('name', '').strip()
        first_name = contact.get('first_name', '').strip()
        last_name = contact.get('last_name', '').strip()

        if not first_name and full_name:
            parts = full_name.split()
            first_name = parts[0]
            if not last_name and len(parts) > 1:
                last_name = ' '.join(parts[1:])

        if not full_name:
            full_name = f"{first_name} {last_name}".strip()

        username = contact.get('username', '').strip()
        formatted_username = f"@{username.lstrip('@')}" if username else ""
        phone = contact.get('phone', '').strip()
        user_id = str(contact.get('user_id', '')).strip()

        # Build replacement dictionary
        replacements = {
            'first_name': first_name or default_name,
            'last_name': last_name or "",
            'name': full_name or default_name,
            'username': formatted_username,
            'phone': phone,
            'user_id': user_id,
        }

        # Include any custom fields from CSV (e.g., company, title, product)
        for k, v in contact.items():
            if k not in replacements and v is not None:
                replacements[k] = str(v)

        # Substitute variable placeholders
        rendered = template
        for key, val in replacements.items():
            rendered = rendered.replace(f"{{{key}}}", str(val))

        # Evaluate spintax on the personalized text
        return cls.spin_text(rendered)

    @classmethod
    def generate_previews(cls, template: str, sample_contacts: List[Dict], count: int = 3) -> List[str]:
        """Generate diverse preview variations for verification before running campaigns."""
        previews = []
        contacts_to_use = sample_contacts[:count] if sample_contacts else [{}]
        
        for contact in contacts_to_use:
            rendered = cls.render_template(template, contact)
            previews.append(rendered)
            
        return previews
