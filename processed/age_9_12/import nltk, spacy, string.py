import nltk, spacy, string
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, WordNetLemmatizer
from nltk import pos_tag

# One-time downloads
nltk.download('punkt'); nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger'); nltk.download('wordnet')

nlp = spacy.load("en_core_web_sm")
text = input("Enter text: ")

# a) Tokenization
sents = sent_tokenize(text)
words = word_tokenize(text)

# b) Stopword removal
sw = set(stopwords.words('english'))
words = [w for w in words if w.lower() not in sw]

# c) Remove punctuation
words = [w for w in words if w not in string.punctuation]

# d) POS tagging
print("Sentences:", sents)
print("Words:", words)
print("POS (NLTK):", pos_tag(words))

# e) Stemming & Lemmatization
ps = PorterStemmer()
lm = WordNetLemmatizer()

print("Stemmed:", [ps.stem(w) for w in words])
print("Lemma (NLTK):", [lm.lemmatize(w) for w in words])

doc = nlp(text)
print("Lemma (spaCy):", [t.lemma_ for t in doc if t.text not in string.punctuation])
print("POS (spaCy):", [(t.text, t.pos_) for t in doc])