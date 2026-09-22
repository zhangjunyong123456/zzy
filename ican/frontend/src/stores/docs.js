import { defineStore } from 'pinia'
import { listDocuments, uploadDocument, deleteDocument } from '../api/documents'

export const useDocsStore = defineStore('docs', {
  state: () => ({
    docs: [],
    uploading: false,
    loading: false
  }),
  actions: {
    async load() {
      this.loading = true
      try {
        this.docs = await listDocuments()
      } finally {
        this.loading = false
      }
    },
    async upload(file, scene) {
      this.uploading = true
      try {
        await uploadDocument(file, scene)
        await this.load()
        return null
      } catch (e) {
        return e.message
      } finally {
        this.uploading = false
      }
    },
    async remove(id) {
      await deleteDocument(id)
      await this.load()
    }
  }
})
