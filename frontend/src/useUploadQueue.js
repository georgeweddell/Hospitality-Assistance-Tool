import { useRef, useState } from 'react'
import { readUpload } from './imports'

// Several files of one kind (e.g. a month's invoices), reviewed one after
// another. The next file is read while the owner checks the current one, so
// there's no wait between reviews.
//
//   start(kind, files)  begin with the first file
//   current             { upload } ready to review, { error } if it couldn't be
//                       read, or null while it's still being read
//   next()              move on (after Apply, Cancel or Skip); calls onFinished
//                       after the last file
export default function useUploadQueue(onFinished) {
  const [kind, setKind] = useState(null)
  const [files, setFiles] = useState([])
  const [index, setIndex] = useState(0)
  const [results, setResults] = useState({})   // file index -> { upload } | { error }
  const batch = useRef(0)   // a read from an earlier batch mustn't land in this one

  const read = (k, list, i) => {
    if (i >= list.length) return
    const mine = batch.current
    const keep = (result) => { if (batch.current === mine) setResults((r) => ({ ...r, [i]: result })) }
    readUpload(k, list[i])
      .then((upload) => keep({ upload }))
      .catch((err) => keep({ error: `${list[i].name}: ${err.message}` }))
  }

  const start = (k, fileList) => {
    const list = [...fileList]
    batch.current += 1
    setKind(k)
    setFiles(list)
    setIndex(0)
    setResults({})
    read(k, list, 0)
    read(k, list, 1)
  }

  const next = () => {
    const i = index + 1
    if (i >= files.length) {
      setKind(null)
      setFiles([])
      setResults({})
      onFinished()
      return
    }
    setIndex(i)
    read(kind, files, i + 1)   // i itself was started one step earlier
  }

  return {
    active: files.length > 0,
    kind,
    position: index + 1,
    total: files.length,
    current: results[index] ?? null,
    start,
    next,
  }
}
