import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface AgentSummaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  playerId: string | null;
  summary: any;
  isLoading?: boolean;
  error?: string | null;
}

const AgentSummaryModal: React.FC<AgentSummaryModalProps> = ({ 
  isOpen, 
  onClose, 
  playerId, 
  summary,
  isLoading = false,
  error = null
}) => {
  const [currentSection, setCurrentSection] = useState<string>('overview');
  
  // Close modal on Escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 flex items-center justify-center z-50"
          onClick={onClose}
        >
          <div className="absolute inset-0 bg-black bg-opacity-40"></div>
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="relative bg-gray-900 border-2 border-green-400 rounded-lg w-11/12 max-w-4xl max-h-[90vh] overflow-hidden z-10"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Terminal Header */}
            <div className="flex items-center justify-between border-b border-green-400 p-4">
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                  <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                </div>
                <div className="text-green-400 text-lg font-mono">
                  {playerId ? `${playerId}_agent_summary.log` : 'loading...'}
                </div>
              </div>
              <button
                onClick={onClose}
                className="text-green-400 hover:text-green-300 text-xl font-mono font-bold px-3 py-1 border border-green-400 rounded hover:bg-gray-800 transition-colors"
              >
                ×
              </button>
            </div>

            {/* Terminal Content */}
            <div className="p-6 overflow-y-auto max-h-[70vh] bg-gray-900 text-green-300 font-mono">
              {isLoading ? (
                <div className="text-center py-12">
                  <div className="text-green-400 text-lg mb-4">$ loading agent data...</div>
                  <div className="text-green-300 text-sm">accessing neural networks...</div>
                </div>
              ) : error ? (
                <div className="text-center py-12">
                  <div className="text-red-400 text-lg mb-4">$ error encountered</div>
                  <div className="text-red-300 text-sm">{error}</div>
                </div>
              ) : !summary?.summary ? (
                <div className="text-center py-12">
                  <div className="text-yellow-400 text-lg mb-4">$ cat agent_summary.log</div>
                  <div className="text-yellow-300 text-sm">
                    <span className="text-green-400">{'>'}</span> no data available
                  </div>
                  <div className="text-yellow-300 text-sm mt-2">
                    <span className="text-green-400">{'>'}</span> agent needs to play at least 4 turns
                  </div>
                </div>
              ) : (
                <>
                  {/* Command prompt */}
                  <div className="text-green-400 mb-4">
                    $ cat {playerId}_summary.log
                  </div>

                  {/* Tab Navigation */}
                  <div className="border border-green-400 rounded p-2 mb-4 bg-gray-800">
                    <div className="flex gap-2 flex-wrap">
                      {[
                        { id: 'overview', label: 'overview' },
                        { id: 'players', label: 'players' },
                        { id: 'strategies', label: 'strategies' },
                        { id: 'lessons', label: 'lessons' }
                      ].map((tab) => (
                        <button
                          key={tab.id}
                          onClick={() => setCurrentSection(tab.id)}
                          className={`px-3 py-1 text-sm border transition-colors ${
                            currentSection === tab.id
                              ? 'bg-green-600 text-gray-900 border-green-400'
                              : 'bg-gray-700 text-green-300 border-green-600 hover:bg-gray-600'
                          }`}
                        >
                          {tab.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Tab Content */}
                  <div className="text-sm">
                    {currentSection === 'overview' && (
                      <div className="space-y-4">
                        <div className="border border-green-400 p-4 rounded bg-gray-800">
                          <div className="text-green-400 mb-2">
                            <span className="text-green-400">{'>'}</span> game_reflection:
                          </div>
                          <div className="text-green-300 leading-relaxed ml-4">
                            {summary.summary.game_reflection || 'no reflection data available'}
                          </div>
                        </div>
                        
                        <div className="border border-green-400 p-4 rounded bg-gray-800">
                          <div className="text-green-400 mb-2">
                            <span className="text-green-400">{'>'}</span> summary_info:
                          </div>
                          <div className="grid grid-cols-2 gap-4 text-sm ml-4">
                            <div>
                              <span className="text-green-400">summarized_turns:</span>
                              <div className="text-green-300">{summary.summarized_turns || 0}</div>
                            </div>
                            <div>
                              <span className="text-green-400">last_updated:</span>
                              <div className="text-green-300">turn_{summary.last_updated || 'unknown'}</div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {currentSection === 'players' && (
                      <div className="space-y-4">
                        <div className="text-green-400 mb-4">
                          <span className="text-green-400">{'>'}</span> player_personalities:
                        </div>
                        {summary.summary.player_personalities && Object.keys(summary.summary.player_personalities).length > 0 ? (
                          Object.entries(summary.summary.player_personalities).map(([player, personality]) => (
                            <div key={player} className="border border-green-400 p-4 rounded bg-gray-800 ml-4">
                              <div className="text-green-400 mb-2">{player}:</div>
                              <div className="text-green-300 leading-relaxed">{personality}</div>
                            </div>
                          ))
                        ) : (
                          <div className="text-green-300 text-center py-8 ml-4">
                            no player personality data available
                          </div>
                        )}
                        
                        {summary.summary.threat_assessment && Object.keys(summary.summary.threat_assessment).length > 0 && (
                          <div className="mt-6">
                            <div className="text-green-400 mb-4">
                              <span className="text-green-400">{'>'}</span> threat_assessment:
                            </div>
                            {Object.entries(summary.summary.threat_assessment).map(([player, assessment]) => (
                              <div key={player} className="border border-red-400 p-4 rounded bg-gray-800 ml-4 mb-2">
                                <div className="text-red-400 mb-2">{player}:</div>
                                <div className="text-green-300 leading-relaxed">{assessment}</div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {currentSection === 'strategies' && (
                      <div className="space-y-6">
                        <div>
                          <div className="text-green-400 mb-4">
                            <span className="text-green-400">{'>'}</span> strategies_that_work:
                          </div>
                          {summary.summary.strategies_that_work && summary.summary.strategies_that_work.length > 0 ? (
                            <div className="space-y-2 ml-4">
                              {summary.summary.strategies_that_work.map((strategy: string, index: number) => (
                                <div key={index} className="border border-green-400 p-3 rounded bg-gray-800 flex items-start gap-3">
                                  <div className="text-green-400">✓</div>
                                  <div className="text-green-300">{strategy}</div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="text-green-300 text-center py-4 ml-4">
                              no successful strategies recorded
                            </div>
                          )}
                        </div>

                        <div>
                          <div className="text-red-400 mb-4">
                            <span className="text-red-400">{'>'}</span> strategies_to_avoid:
                          </div>
                          {summary.summary.strategies_to_avoid && summary.summary.strategies_to_avoid.length > 0 ? (
                            <div className="space-y-2 ml-4">
                              {summary.summary.strategies_to_avoid.map((strategy: string, index: number) => (
                                <div key={index} className="border border-red-400 p-3 rounded bg-gray-800 flex items-start gap-3">
                                  <div className="text-red-400">✗</div>
                                  <div className="text-green-300">{strategy}</div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="text-green-300 text-center py-4 ml-4">
                              no failed strategies recorded
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {currentSection === 'lessons' && (
                      <div className="space-y-4">
                        <div className="text-green-400 mb-4">
                          <span className="text-green-400">{'>'}</span> key_lessons_learned:
                        </div>
                        {summary.summary.key_lessons && summary.summary.key_lessons.length > 0 ? (
                          <div className="space-y-3 ml-4">
                            {summary.summary.key_lessons.map((lesson: string, index: number) => (
                              <div key={index} className="border border-green-400 p-4 rounded bg-gray-800 flex items-start gap-3">
                                <div className="text-green-400">#{index + 1}</div>
                                <div className="text-green-300 leading-relaxed">{lesson}</div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-green-300 text-center py-8 ml-4">
                            no lessons learned data available
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>

            {/* Terminal Footer */}
            <div className="border-t border-green-400 p-3 text-center bg-gray-800">
              <div className="text-green-400 text-sm font-mono">
                [ESC] exit • [CLICK] navigate
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default AgentSummaryModal; 