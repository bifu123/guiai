import os
import yaml
import json
from gui_vl import glm_4_6v_flash

class SkillManager:
    def __init__(self, skills_dir="./skills"):
        self.skills_dir = skills_dir
        self.skills = self._load_skills()

    def _load_skills(self):
        skills = {}
        if not os.path.exists(self.skills_dir):
            return skills

        for folder_name in os.listdir(self.skills_dir):
            folder_path = os.path.join(self.skills_dir, folder_name)
            if os.path.isdir(folder_path):
                skill_file = os.path.join(folder_path, "SKILL.md")
                if os.path.exists(skill_file):
                    try:
                        with open(skill_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Parse YAML frontmatter
                        if content.startswith('---'):
                            parts = content.split('---', 2)
                            if len(parts) >= 3:
                                frontmatter = yaml.safe_load(parts[1])
                                markdown_content = parts[2].strip()
                                
                                name = frontmatter.get('name')
                                description = frontmatter.get('description')
                                
                                if name and name == folder_name:
                                    skills[name] = {
                                        "name": name,
                                        "description": description,
                                        "content": markdown_content
                                    }
                                else:
                                    print(f"[Warning] Skill name mismatch or missing in {skill_file}")
                    except Exception as e:
                        print(f"[Error] Failed to load skill {skill_file}: {e}")
        return skills

    def select_skill(self, intent):
        if not self.skills:
            return None

        skill_descriptions = []
        for name, skill in self.skills.items():
            skill_descriptions.append(f"- {name}: {skill['description']}")
        
        skills_list_str = "\n".join(skill_descriptions)

        prompt = f"""
请根据用户的任务意图，从以下可用技能中选择一个最相关的技能。

【用户意图】:
{intent}

【可用技能】:
{skills_list_str}

请判断哪个技能最适合完成该任务。
如果找到合适的技能，请严格输出 JSON 格式：
{{
    "selected_skill": "技能名称"
}}

如果没有合适的技能，请严格输出 JSON 格式：
{{
    "selected_skill": "none"
}}
"""
        try:
            # We use the text-only capability of the VLM or just pass a dummy image if required by the API.
            # Assuming glm_4_6v_flash can handle text-only if image is empty or we pass a 1x1 pixel.
            # Let's check how glm_4_6v_flash is implemented. It usually requires an image.
            # For simplicity, we can just use the same function with a dummy image or if it supports text only.
            # Wait, we can just use a text LLM for this, but to avoid adding new dependencies, 
            # let's see if we can use glm_4_6v_flash with a blank image.
            # Actually, let's just use the text model if available, or pass a dummy base64 image.
            dummy_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
            response_text = glm_4_6v_flash(prompt, dummy_image)
            
            # Parse JSON
            import re
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
                
            match = re.search(r'\{.*\}', json_str, re.DOTALL)
            if match:
                result = json.loads(match.group())
                selected = result.get("selected_skill")
                if selected and selected in self.skills:
                    print(f"[SkillManager] Selected skill: {selected}")
                    return self.skills[selected]["content"]
            
            print("[SkillManager] No specific skill selected.")
            return None
        except Exception as e:
            print(f"[SkillManager] Error selecting skill: {e}")
            return None

skill_manager = SkillManager()
