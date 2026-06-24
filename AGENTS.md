# Automato — Agent Guide
The project is a collection of semanically structured Python modules.

## Common
Use **English** for literals.
Use **Python** by default.

## Python
- Inline dependencies for use `uv run`.
- Add shebang to executable script.
- Do `chmod +x` for executive script. 

## Code Styling
- the code should be according to the
best practices, clean, understandable and contain nothing superfluous
- follow DRY, Single Responsibility, KISS, YAGNI, don't produce extra entities
- write code according to my assignment, first discuss your options and ideas with me - the code should be commented on, especially the functions, accepted values and return results
- the code should look like written Senior developer
- code should be environment-agnostic
- clients should be concise, simple and revealing the functions, its parameters and return result must have type-hints

## CLI integration 
Each module can be called from console - don't worry about - just add:
```
def main():
.   lib.CLI(<Short single-line description>, <reference to this module>).run()
```

### REGISTRY.md
Before task planning read REGISTRY.md - enumeration of existed modules and method with short description for you.
Format: `util:method - short and consize description`.  
Keep list up to date
