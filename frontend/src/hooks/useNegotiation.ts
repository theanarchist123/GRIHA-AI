import { useState, useEffect } from 'react';
import { ApiClient } from '@/lib/api-client';

export function useNegotiation(propertyId: string | null) {
  const [strategy, setStrategy] = useState<any>(null);
  const [negotiationId, setNegotiationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!propertyId) return;

    const fetchNegotiation = async () => {
      setLoading(true);
      setError(null);
      try {
        const json = await ApiClient.get(`/api/negotiation/property/${propertyId}`);
        if (json.status === "success" && json.data) {
          setStrategy(json.strategy);
          setNegotiationId(json.data.id);
        }
      } catch (err: any) {
        setError(err.message || "Failed to fetch negotiation");
      } finally {
        setLoading(false);
      }
    };

    fetchNegotiation();
  }, [propertyId]);

  return { strategy, negotiationId, loading, error };
}
