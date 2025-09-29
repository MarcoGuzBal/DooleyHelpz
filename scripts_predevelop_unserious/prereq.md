Thoughts on Prerequisite Structure
	•	Outer list = AND → every group must be satisfied
	•	Inner list = OR → at least one course in the group must be taken

⸻

Example:
'''
{
  "prerequisites": [
    ["CS 170", "CS_OX 170"],
    ["CS 171", "CS_OX 171"],
    ["CS 224", "CS_OX 224"],
    ["CS 253"]
  ]
}
'''

Meaning:
A student must complete (CS 170 or CS_OX 170) AND (CS 171 or CS_OX 171) AND (CS 224 or CS_OX 224) AND CS 253.