"use client";

import { useEffect, useState } from "react";
import { DashboardSidebar, DashboardTopBar } from "@/components/shared/Navbar";
import { FileText, Loader2, AlertTriangle, XCircle, ShieldCheck, PenTool } from "lucide-react";
import Link from "next/link";
import { formatPrice } from "@/lib/utils";

export default function DocumentDetailsPage({ params }: { params: { id: string } }) {
  const [doc, setDoc] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [rewritingClause, setRewritingClause] = useState<number | null>(null);

  useEffect(() => {
    fetchDoc();
  }, [params.id]);

  async function fetchDoc() {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}/api/documents/`);
      const json = await res.json();
      if (json.status === "success") {
        const found = json.data.find((d: any) => d.id === params.id);
        setDoc(found);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleRewrite(clauseIndex: number, clause: any) {
    setRewritingClause(clauseIndex);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}/api/documents/rewrite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          clause_text: clause.text,
          risk_level: clause.risk_level,
          problem: clause.problem,
          recommendation: clause.recommendation,
          doc_type: doc.document_type
        })
      });
      const json = await res.json();
      if (json.status === "success") {
        // Update the doc locally to show the rewritten clause
        setDoc((prev: any) => {
          const newDoc = { ...prev };
          const clauses = [...newDoc.clause_analysis];
          clauses[clauseIndex] = {
            ...clauses[clauseIndex],
            rewritten_text: json.rewritten_clause
          };
          newDoc.clause_analysis = clauses;
          return newDoc;
        });
      }
    } catch (err) {
      console.error("Rewrite failed", err);
    } finally {
      setRewritingClause(null);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-cream flex flex-col">
        <DashboardSidebar />
        <div className="lg:ml-[260px] flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-forest" />
        </div>
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="min-h-screen bg-cream flex flex-col">
        <DashboardSidebar />
        <div className="lg:ml-[260px] flex-1 flex items-center justify-center">
          <p>Document not found.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-cream flex flex-col">
      <DashboardSidebar />
      <div className="lg:ml-[260px]">
        <DashboardTopBar />
        <div className="p-4 sm:p-6 max-w-5xl">
          <Link href="/documents" className="text-sm font-dm text-muted hover:text-charcoal mb-4 inline-block">&larr; Back to Documents</Link>
          <div className="flex items-center gap-4 mb-6">
            <div className="w-12 h-12 bg-forest/10 rounded-xl flex items-center justify-center shrink-0">
              <FileText className="w-6 h-6 text-forest" />
            </div>
            <div>
              <h1 className="font-playfair text-2xl text-charcoal">{doc.filename}</h1>
              <p className="text-sm font-dm text-muted capitalize">{doc.document_type.replace('_', ' ')}</p>
            </div>
          </div>

          {doc.ai_summary && (
            <div className="bg-surface rounded-2xl p-6 border border-border-custom mb-8 shadow-sm">
              <h3 className="font-dm font-bold text-charcoal text-sm uppercase tracking-wider mb-2">AI Summary</h3>
              <p className="text-sm font-dm text-charcoal leading-relaxed">{doc.ai_summary}</p>
            </div>
          )}

          <h2 className="font-playfair text-xl text-charcoal mb-4">Clause Analysis</h2>
          <div className="space-y-4">
            {doc.clause_analysis?.map((clause: any, idx: number) => {
              const isHighRisk = clause.risk_level === "high";
              const isCaution = clause.risk_level === "caution";
              const isStandard = clause.risk_level === "standard";
              
              return (
                <div key={idx} className={`bg-surface rounded-2xl p-6 border shadow-sm ${isHighRisk ? 'border-danger/30 bg-danger/5' : isCaution ? 'border-warm-gold/30 bg-warm-gold/5' : 'border-border-custom'}`}>
                  <div className="flex justify-between items-start mb-4">
                    <h3 className="font-dm font-bold text-charcoal">{clause.heading || `Clause ${clause.clause_number}`}</h3>
                    {isHighRisk && <span className="inline-flex items-center gap-1 text-[10px] bg-danger/10 text-danger px-2 py-1 rounded-full font-bold uppercase"><XCircle className="w-3 h-3" /> High Risk</span>}
                    {isCaution && <span className="inline-flex items-center gap-1 text-[10px] bg-warm-gold/10 text-warm-gold px-2 py-1 rounded-full font-bold uppercase"><AlertTriangle className="w-3 h-3" /> Caution</span>}
                    {isStandard && <span className="inline-flex items-center gap-1 text-[10px] bg-success/10 text-success px-2 py-1 rounded-full font-bold uppercase"><ShieldCheck className="w-3 h-3" /> Standard</span>}
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <p className="text-xs font-dm font-bold text-muted uppercase mb-1">Original Text</p>
                      <p className="text-sm font-dm text-charcoal bg-white p-3 rounded-xl border border-charcoal/10 h-full">{clause.text}</p>
                    </div>
                    
                    <div className="flex flex-col gap-4">
                      {clause.rewritten_text ? (
                        <div>
                          <p className="text-xs font-dm font-bold text-forest uppercase mb-1">AI Rewritten Clause</p>
                          <p className="text-sm font-dm text-forest bg-forest/10 border border-forest/20 p-3 rounded-xl">{clause.rewritten_text}</p>
                        </div>
                      ) : (
                        <>
                          <div>
                            <p className="text-xs font-dm font-bold text-muted uppercase mb-1">Meaning</p>
                            <p className="text-sm font-dm text-charcoal">{clause.meaning}</p>
                          </div>
                          {(isHighRisk || isCaution) && (
                            <div>
                              <p className="text-xs font-dm font-bold text-danger uppercase mb-1">Problem & Recommendation</p>
                              <p className="text-sm font-dm text-charcoal">{clause.problem} <br/><span className="text-muted">{clause.recommendation}</span></p>
                            </div>
                          )}
                          
                          {(isHighRisk || isCaution) && (
                            <button 
                              onClick={() => handleRewrite(idx, clause)}
                              disabled={rewritingClause === idx}
                              className="mt-auto self-start px-4 py-2 bg-charcoal text-white rounded-xl text-sm font-dm font-semibold hover:bg-black transition-colors flex items-center gap-2"
                            >
                              {rewritingClause === idx ? <Loader2 className="w-4 h-4 animate-spin" /> : <PenTool className="w-4 h-4" />}
                              Rewrite Clause
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
