def has_key(hash_table, key: str) -> bool:
  try:
    hash_table[key]
    return True
  except:
    return False

def ask_y_n(question: str, yes_action, no_action):
  while True:
      answer = input(question + " (Yes/No) ")
      if len(answer) == 0:
          continue
      elif answer[:1].lower() in 'y':
          yes_action()
          return
      elif answer[:1].lower() in 'n':
          no_action()

