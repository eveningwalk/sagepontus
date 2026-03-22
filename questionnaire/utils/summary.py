# utils/summary.py

from transformers import T5Tokenizer, T5ForConditionalGeneration

tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-base")
model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-base")

'''
def summarize_text(text: str) -> str:
    input_text = "summarize: " + text
    input_ids = tokenizer(input_text, return_tensors="pt").input_ids
    output_ids = model.generate(input_ids, max_length=150, num_beams=2)
    return tokenizer.decode(output_ids[0], skip_special_tokens=True)
'''
def summarize_text(text: str) -> str:
    try:
        #input_text = "summarize: " + text
        #input_text = f"Please summarize the following article in 3-4 sentences:\n\n{text}"
        input_text = f"다음 내용을 요약해줘:\n\n{text}"

        print("\n\n input_text", input_text, len(input_text))
        input_ids = tokenizer(input_text, return_tensors="pt").input_ids
        #output_ids = model.generate(input_ids, max_length=150, num_beams=2
        output_ids = model.generate(
                input_ids,
                max_length=150,
                min_length=30,
                num_beams=4,
                early_stopping=True,
                no_repeat_ngram_size=2,
            )

        return tokenizer.decode(output_ids[0], skip_special_tokens=True)
    except Exception as e:
        print("요약 중 오류:", e)
        return "요약을 생성하는 중 오류가 발생했습니다."
