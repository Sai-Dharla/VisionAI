// React & ReactDOM are loaded as globals via CDN in index.html
const { useState, useRef } = React;

// Helper component to render attribute cards
function AttributeCard({label, value, icon}) {
  return (
    <div className="flex items-center space-x-2 p-3 bg-white rounded-lg shadow">
      {/* Simple placeholder icon; replace with proper SVG if desired */}
      <span className="text-indigo-600 font-semibold">{icon}</span>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-base font-medium text-gray-800">{value}</p>
      </div>
    </div>
  );
}

function SimilarImage({url, name}) {
  return (
    <div className="w-32 h-32 rounded overflow-hidden shadow">
      <img src={url} alt={name} className="w-full h-full object-cover" />
    </div>
  );
}

function ImageUpload() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setPreview(URL.createObjectURL(selectedFile));
      setResult(null);
      setError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select an image.');
      return;
    }
    setLoading(true);
    setError('');
    const form = new FormData();
    form.append('image', file);
    try {
      const resp = await fetch('/api/predict/', {
        method: 'POST',
        body: form,
      });
      const data = await resp.json();
      if (!resp.ok) {
        setError(data.error || 'Server error');
      } else {
        setResult(data);
      }
    } catch (err) {
      setError('Network error');
    } finally {
      setLoading(false);
    }
  };

  const clearSelection = () => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError('');
    if (fileInputRef.current) fileInputRef.current.value = null;
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center p-4">
      {/* Header */}
      <header className="w-full max-w-4xl flex justify-between items-center py-4">
        <h1 className="text-2xl font-bold text-indigo-800">VisionAI Dashboard</h1>
        <a href="#" className="text-sm text-indigo-600 hover:underline">Help & Docs</a>
      </header>

      {/* Upload Panel */}
      <section className="w-full max-w-4xl bg-white rounded-xl shadow-md p-6 mb-8">
        <form onSubmit={handleSubmit} className="space-y-4">
          {!preview ? (
            <div
              className="border-2 border-dashed border-indigo-300 rounded-lg p-8 text-center cursor-pointer hover:border-indigo-500 transition"
              onClick={() => fileInputRef.current.click()}
            >
              <p className="text-indigo-600 font-medium">Click to select an image or drag & drop</p>
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept=".jpg,.jpeg,.png,.webp"
                onChange={handleFileChange}
              />
            </div>
          ) : (
            <div className="relative">
              <img src={preview} alt="preview" className="w-full max-h-80 object-contain rounded" />
              <button
                type="button"
                onClick={clearSelection}
                className="absolute top-2 right-2 bg-white bg-opacity-75 rounded-full p-1 text-gray-600 hover:text-gray-800"
              >
                ✕
              </button>
            </div>
          )}

          {error && (
            <p className="text-red-600 bg-red-50 p-2 rounded">{error}</p>
          )}

          <button
            type="submit"
            disabled={!file || loading}
            className={`w-full py-2 rounded ${!file ? 'bg-gray-300 cursor-not-allowed' : loading ? 'bg-indigo-400' : 'bg-indigo-600 hover:bg-indigo-700'} text-white font-semibold transition`}
          >
            {loading ? 'Analyzing...' : 'Identify Image'}
          </button>
        </form>
      </section>

      {/* Result Panel */}
      {result && (
        <section className="w-full max-w-4xl bg-white rounded-xl shadow-md p-6">
          {/* Tag */}
          <span className="inline-block px-3 py-1 bg-indigo-100 text-indigo-800 rounded-full text-sm font-medium mb-4">{result.tag}</span>

          {/* Title */}
          <h2 className="text-xl font-bold text-gray-800 mb-2">{result.class_name} ({result.confidence})</h2>

          {/* Description */}
          <p className="text-gray-700 mb-4">{result.description}</p>

          {/* Attributes Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 mb-6">
            {result.attributes.map((attr, idx) => (
              <AttributeCard key={idx} label={attr.label} value={attr.value} icon={attr.icon} />
            ))}
          </div>

          {/* Similar Images */}
          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-2">Similar Images</h3>
            <div className="flex space-x-3 overflow-x-auto">
              {result.similar_images.map((img, idx) => (
                <SimilarImage key={idx} url={img.url} name={img.name} />
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<ImageUpload />);
