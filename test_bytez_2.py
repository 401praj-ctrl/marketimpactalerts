from bytez import Bytez
import json

sdk = Bytez("ca841bcfa13211efb6f53e6b4c34c77f")
model = sdk.model("Qwen/Qwen3-0.6B")
result = model.run([{"role": "user", "content": "Hi"}])
print(result)
