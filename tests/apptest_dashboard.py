import os, tempfile; os.environ["ASA_WORKDIR"] = tempfile.mkdtemp()
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("../dashboard/app.py", default_timeout=30)
at.run()
assert not at.exception, at.exception
at.sidebar.button[0].click().run()
assert not at.exception, at.exception
for b in at.button:
    if b.label.startswith("Generate"): b.click().run(); break
assert not at.exception, at.exception
for b in at.button:
    if b.label.startswith("Issue"): b.click().run(); break
assert not at.exception, at.exception
for b in at.button:
    if b.label=="Mark paid": b.click().run(); break
print("exc", at.exception, [m.value for m in at.metric], [x.value for x in at.success])
at.chat_input[0].set_value("how much?").run()
print([m.markdown[0].value for m in at.chat_message][-1][:100])
