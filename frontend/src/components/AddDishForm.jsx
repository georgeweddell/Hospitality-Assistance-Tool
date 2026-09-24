import { useState, useEffect } from 'react'
import { postJson } from '../api'
import Card from './Card'

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
    <Card title="Add a dish">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Dish name"
          className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-ink focus:border-accent focus:outline-none"
        />

        <input
          type="number"
          value={menuPrice}
          onChange={(e) => setMenuPrice(e.target.value)}
          placeholder="Menu price (£)"
          className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-ink focus:border-accent focus:outline-none"
        />

        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-ink focus:border-accent focus:outline-none"
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
          className="rounded-lg bg-accent px-4 py-2 font-medium text-accent-ink hover:opacity-90 disabled:opacity-50"
        >
          {submitting ? "Saving…" : "Add dish"}
        </button>

        {error && <p className="text-sm text-danger">{error}</p>}
      </form>
    </Card>
  );
}

export default AddDishForm