from text2cypher.pipeline import Text2CypherPipeline


with Text2CypherPipeline() as pipeline:

    result = pipeline.ask(
        "اطلاعاتی که از استیوجابز موجود هست بهم بده"
    )


print("Answer:")
print(result["answer"])

print("\nCypher:")
print(result["cypher"])

print("\nAttempts:")
print(result["attempts"])

print("\nRows:")
print(result["rows"])

print("\nEvidence:")
print(result["evidence"])

print("\nErrors:")
print(result["errors"])