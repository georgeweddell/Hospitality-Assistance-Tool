import { useState, useEffect } from 'react'
import { postJson } from '../api'

function AddDishForm({ onDishAdded }) {
  const [name, setName] = useState("");
  const [menuPrice, setMenuPrice] = useState("");
  const [category, setCategory] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = (e) => {
    e.preventDefault();

    if (name.trim() === "" || menuPrice === "") {
      setError("Name and menu price are required.");
      return;
    }

    setSubmitting(true);
    setError(null);

    postJson('/dishes', {
      name: name.trim(),
      menu_price: Number(menuPrice),
      category: category === "" ? null : category,
    })
      .then(() => {
        setName("");
        setMenuPrice("");
        setCategory("");
        onDishAdded();
      })
      .catch((err) => setError(err.message))
      .finally(() => setSubmitting(false));
  };

  return (
    <div className="card">
      <h2 className="text-xl font-semibold mb-3">Add a dish</h2>

      <form onSubmit={handleSubmit} className="flex flex-col gap-2 max-w-xs">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Dish name"
          className="border rounded px-2 py-1"
        />

        <input
          type="number"
          value={menuPrice}
          onChange={(e) => setMenuPrice(e.target.value)}
          placeholder="Menu price (£)"
          className="border rounded px-2 py-1"
        />

        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="border rounded px-2 py-1"
        >
          <option value="">Select a category…</option>
          <option value="Starter">Starter</option>
          <option value="Main">Main</option>
          <option value="Side">Side</option>
          <option value="Dessert">Dessert</option>
        </select>

        <button
          type="submit"
          disabled={submitting}
          className="bg-slate-800 text-white rounded px-3 py-1 disabled:opacity-50"
        >
          {submitting ? "Saving…" : "Add dish"}
        </button>

        {error && <p className="text-sm text-red-600">{error}</p>}
      </form>
    </div>
  );
}

export default AddDishForm